"""
Database Manager for Oracle ADB Wallet Connection
Implements connection pooling, transaction management, and Oracle-specific features
using Oracle Autonomous Database wallet-based authentication
"""

import os
import oracledb
from dotenv import load_dotenv
import json
import threading
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

from config import Config
from logger import get_logger

# ✅ Load environment variables from .env
load_dotenv()
logger = get_logger(__name__)

# ✅ Force thin mode before any connection attempt
oracledb.defaults.force_thin_mode = True
print("Using Thin Mode:", oracledb.is_thin_mode())


class OracleConnectionError(Exception):
    """Custom exception for Oracle connection issues"""
    pass


class DatabaseManager:
    """
    Database Manager implementing Oracle ADB wallet connection patterns
    Uses Oracle Autonomous Database with wallet-based authentication
    """
    
    def __init__(self):
        self.username = os.getenv("ORACLE_USERNAME")
        self.password = os.getenv("ORACLE_PASSWORD")
        self.dsn = os.getenv("ORACLE_DSN")  # e.g., "testmcp_tp"
        self.wallet_path = os.getenv("ORACLE_WALLET_LOCATION")
        self.wallet_password = os.getenv("ORACLE_WALLET_PASSWORD")
        

        # Sanity check for required env vars
        if not all([self.username, self.password, self.dsn, self.wallet_path]):
            raise OracleConnectionError("Missing required Oracle DB environment variables")

    def _get_connection(self):
        """
        Establish a wallet-secured connection to Oracle ADB
        """
        try:
            conn = oracledb.connect(
                user=self.username,
                password=self.password,
                dsn=self.dsn,
                config_dir=self.wallet_path,
                wallet_location=self.wallet_path,
                wallet_password=self.wallet_password,  # ✅ DO NOT pass any password!
                ssl_server_dn_match=True
            )
            logger.info("✅ Connected to Oracle DB")
            return conn
        except Exception as e:
            logger.error(f"❌ Oracle DB connection failed: {str(e)}")
            raise OracleConnectionError(f"Oracle DB connection failed: {str(e)}")

    def test_connection(self):
        """
        Runs a simple query to test DB connection
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 'Hello from Oracle!' FROM dual")
                for row in cursor:
                    print(row[0])
            conn.close()
            return True
        except Exception as e:
            logger.error("❌ Test query failed")
            raise



    def _get_config(self, var_name: str) -> str:
        """Get required configuration value"""
        value = os.environ.get(var_name)
        if not value:
            raise ValueError(f"Missing required environment variable: {var_name}")
        return value




    @contextmanager
    def _connection_context(self):
        """Context manager for Oracle database connections"""
        conn = None
        try:
            conn = self._get_connection()
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute SQL query with Oracle database
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            Dictionary with query results in standardized format
        """
        start_time = datetime.now()
        
        try:
            with self._connection_context() as conn:
                cursor = conn.cursor()
                
                # Log query execution
                self._log_query_execution(query, parameters)
                
                # Execute query
                if parameters:
                    if isinstance(parameters, dict):
                        # Named parameters
                        cursor.execute(query, parameters)
                    else:
                        # Positional parameters
                        cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                # Get results
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    columns = [col[0] for col in cursor.description]
                    
                    # Convert to list of dictionaries
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            # Handle Oracle-specific types
                            if isinstance(value, cx_Oracle.LOB):
                                value = value.read()
                            elif isinstance(value, cx_Oracle.Datetime):
                                value = str(value)
                            row_dict[columns[i]] = value
                        data.append(row_dict)
                    
                    result = {
                        "status": "success",
                        "data": data,
                        "columns": columns,
                        "row_count": len(data)
                    }
                else:
                    # DML operations
                    conn.commit()
                    result = {
                        "status": "success",
                        "rows_affected": cursor.rowcount,
                        "last_row_id": cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
                    }
                
                # Add execution metadata
                execution_time = (datetime.now() - start_time).total_seconds()
                result.update({
                    "execution_time": execution_time,
                    "timestamp": start_time.isoformat()
                })
                
                logger.info(f"Query executed successfully in {execution_time:.3f}s")
                return result
                
        except cx_Oracle.Error as e:
            error_msg = f"Oracle database error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_code": "ORACLE_ERROR",
                "timestamp": start_time.isoformat()
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_code": "GENERAL_ERROR",
                "timestamp": start_time.isoformat()
            }
    
    def begin_transaction(self):
        """Begin a new transaction"""
        thread_id = threading.get_ident()
        
        try:
            conn = self._get_connection()
            conn.autocommit = False
            
            with self.pool_lock:
                self.transaction_connections[thread_id] = conn
            
            logger.info(f"Transaction started for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            raise
    
    def commit_transaction(self):
        """Commit current transaction"""
        thread_id = threading.get_ident()
        
        try:
            with self.pool_lock:
                conn = self.transaction_connections.get(thread_id)
                
            if conn:
                conn.commit()
                conn.close()
                
                with self.pool_lock:
                    del self.transaction_connections[thread_id]
                
                logger.info(f"Transaction committed for thread {thread_id}")
            else:
                raise Exception("No active transaction found")
                
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            raise
    
    def rollback_transaction(self):
        """Rollback current transaction"""
        thread_id = threading.get_ident()
        
        try:
            with self.pool_lock:
                conn = self.transaction_connections.get(thread_id)
                
            if conn:
                conn.rollback()
                conn.close()
                
                with self.pool_lock:
                    del self.transaction_connections[thread_id]
                
                logger.info(f"Transaction rolled back for thread {thread_id}")
            else:
                logger.warning("No active transaction to rollback")
                
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise
    
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            schema_info = {
                "database_type": "Oracle Autonomous Database",
                "tables": [],
                "total_tables": 0,
                "total_indexes": 0,
                "version": "",
                "wallet_configured": bool(self.wallet_location)
            }
            
            with self._connection_context() as conn:
                cursor = conn.cursor()
                
                # Get database version
                cursor.execute("SELECT * FROM v$version WHERE banner LIKE 'Oracle%'")
                version = cursor.fetchone()
                schema_info["version"] = version[0] if version else "Unknown"
                
                # Get table information
                cursor.execute("""
                    SELECT table_name 
                    FROM all_tables 
                    WHERE owner = :owner
                    ORDER BY table_name
                """, {"owner": self.username.upper()})
                
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    table_info = self._get_table_info(cursor, table_name)
                    schema_info["tables"].append(table_info)
                    schema_info["total_tables"] += 1
                
                # Get index count
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM all_indexes 
                    WHERE owner = :owner
                """, {"owner": self.username.upper()})
                schema_info["total_indexes"] = cursor.fetchone()[0]
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {"error": str(e)}
    
    def _get_table_info(self, cursor, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific table"""
        try:
            # Get column information
            cursor.execute(f"""
                SELECT 
                    column_name, 
                    data_type, 
                    data_length, 
                    nullable, 
                    data_default
                FROM all_tab_columns
                WHERE table_name = :table_name
                AND owner = :owner
                ORDER BY column_id
            """, {"table_name": table_name.upper(), "owner": self.username.upper()})
            
            columns = []
            for col in cursor:
                columns.append({
                    "name": col[0],
                    "type": col[1],
                    "length": col[2],
                    "nullable": col[3] == 'Y',
                    "default": col[4]
                })
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get primary key info
            cursor.execute(f"""
                SELECT cols.column_name
                FROM all_constraints cons, all_cons_columns cols
                WHERE cons.constraint_type = 'P'
                AND cons.constraint_name = cols.constraint_name
                AND cons.owner = cols.owner
                AND cons.owner = :owner
                AND cons.table_name = :table_name
            """, {"table_name": table_name.upper(), "owner": self.username.upper()})
            
            primary_keys = [pk[0] for pk in cursor]
            
            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count,
                "primary_keys": primary_keys,
                "column_count": len(columns)
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {
                "table_name": table_name,
                "error": str(e)
            }
    
    def _log_query_execution(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Log query execution for audit purposes"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query[:200] + "..." if len(query) > 200 else query,
                "parameters": parameters,
                "thread_id": threading.get_ident()
            }
            logger.debug(f"Query execution: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log query execution: {e}")
    
    def close(self):
        """Close all connections and cleanup"""
        try:
            with self.pool_lock:
                # Close transaction connections
                for thread_id, conn in self.transaction_connections.items():
                    try:
                        conn.close()
                    except:
                        pass
                self.transaction_connections.clear()
                
                # Close pooled connections
                for conn in self.connection_pool.values():
                    try:
                        conn.close()
                    except:
                        pass
                self.connection_pool.clear()
            
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.close()