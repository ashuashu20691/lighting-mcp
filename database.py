"""
Database Manager for Oracle ADB Connection Patterns
Implements connection pooling, transaction management, and Oracle-specific features
"""

import sqlite3
import os
import json
import threading
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

from config import Config
from logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """
    Database Manager implementing Oracle ADB connection patterns
    Uses SQLite as backend but implements Oracle-style operations and responses
    """
    
    def __init__(self):
        self.config = Config()
        self.db_path = self.config.database_path
        self.connection_pool = {}
        self.pool_lock = threading.Lock()
        self.max_connections = 10
        self.transaction_connections = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with sample tables for demonstration"""
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Initialize database with sample schema
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create sample tables that simulate Oracle enterprise schema
                self._create_sample_tables(cursor)
                
                # Create indexes
                self._create_indexes(cursor)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_sample_tables(self, cursor):
        """Create sample tables with Oracle-style structure"""
        
        # Employees table (HR schema style)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone_number TEXT,
                hire_date TEXT,
                job_id TEXT,
                salary REAL,
                commission_pct REAL,
                manager_id INTEGER,
                department_id INTEGER,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES employees(employee_id),
                FOREIGN KEY (department_id) REFERENCES departments(department_id)
            )
        """)
        
        # Departments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL,
                manager_id INTEGER,
                location_id INTEGER,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
            )
        """)
        
        # Orders table (Sales schema style)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date TEXT DEFAULT CURRENT_TIMESTAMP,
                ship_date TEXT,
                order_status TEXT CHECK (order_status IN ('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED')),
                total_amount REAL,
                discount_amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                created_by INTEGER,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                product_code TEXT UNIQUE,
                category_id INTEGER,
                unit_price REAL,
                units_in_stock INTEGER DEFAULT 0,
                discontinued INTEGER DEFAULT 0,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit log table (Oracle audit style)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                user_name TEXT,
                session_id TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            )
        """)
        
        # Insert sample data
        self._insert_sample_data(cursor)
    
    def _insert_sample_data(self, cursor):
        """Insert sample data for demonstration"""
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM departments")
        if cursor.fetchone()[0] > 0:
            return  # Data already exists
        
        # Insert departments
        departments = [
            (10, 'Administration', None, 1700),
            (20, 'Marketing', None, 1800),
            (30, 'Purchasing', None, 1700),
            (40, 'Human Resources', None, 2400),
            (50, 'IT', None, 1400),
            (60, 'Finance', None, 1700)
        ]
        
        cursor.executemany("""
            INSERT INTO departments (department_id, department_name, manager_id, location_id)
            VALUES (?, ?, ?, ?)
        """, departments)
        
        # Insert employees
        employees = [
            (100, 'Steven', 'King', 'steven.king@company.com', '515-123-4567', '2020-01-01', 'CEO', 24000, None, None, 10),
            (101, 'Neena', 'Kochhar', 'neena.kochhar@company.com', '515-123-4568', '2020-02-01', 'VP', 17000, None, 100, 10),
            (102, 'Lex', 'De Haan', 'lex.dehaan@company.com', '515-123-4569', '2020-03-01', 'VP', 17000, None, 100, 10),
            (103, 'Alexander', 'Hunold', 'alexander.hunold@company.com', '590-423-4567', '2020-04-01', 'PROG', 9000, None, 102, 50),
            (104, 'Bruce', 'Ernst', 'bruce.ernst@company.com', '590-423-4568', '2020-05-01', 'PROG', 6000, None, 103, 50),
            (105, 'David', 'Austin', 'david.austin@company.com', '590-423-4569', '2020-06-01', 'PROG', 4800, None, 103, 50)
        ]
        
        cursor.executemany("""
            INSERT INTO employees (employee_id, first_name, last_name, email, phone_number, hire_date, job_id, salary, commission_pct, manager_id, department_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, employees)
        
        # Insert products
        products = [
            (1, 'Laptop Computer', 'LAP-001', 1, 1200.00, 50, 0),
            (2, 'Desktop Computer', 'DES-001', 1, 800.00, 30, 0),
            (3, 'Wireless Mouse', 'MOU-001', 2, 25.00, 100, 0),
            (4, 'Keyboard', 'KEY-001', 2, 45.00, 75, 0),
            (5, 'Monitor 24"', 'MON-001', 1, 300.00, 25, 0)
        ]
        
        cursor.executemany("""
            INSERT INTO products (product_id, product_name, product_code, category_id, unit_price, units_in_stock, discontinued)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, products)
        
        # Insert orders
        orders = [
            (1001, 1, '2024-01-15', '2024-01-18', 'DELIVERED', 1245.00, 0, 124.50, 100),
            (1002, 2, '2024-01-16', '2024-01-19', 'DELIVERED', 870.00, 50.00, 87.00, 101),
            (1003, 3, '2024-01-17', None, 'PROCESSING', 325.00, 0, 32.50, 102),
            (1004, 1, '2024-01-18', None, 'PENDING', 1500.00, 100.00, 150.00, 100)
        ]
        
        cursor.executemany("""
            INSERT INTO orders (order_id, customer_id, order_date, ship_date, order_status, total_amount, discount_amount, tax_amount, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, orders)
    
    def _create_indexes(self, cursor):
        """Create indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id)",
            "CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id)",
            "CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email)",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)",
            "CREATE INDEX IF NOT EXISTS idx_products_code ON products(product_code)",
            "CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name, timestamp)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Enable column access by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode for better concurrency
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute SQL query with Oracle-style response formatting
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            Dictionary with query results in Oracle format
        """
        start_time = datetime.now()
        
        try:
            with self._get_connection() as conn:
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
                    columns = [description[0] for description in cursor.description]
                    
                    # Convert to list of dictionaries
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
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
                        "last_row_id": cursor.lastrowid
                    }
                
                # Add execution metadata
                execution_time = (datetime.now() - start_time).total_seconds()
                result.update({
                    "execution_time": execution_time,
                    "timestamp": start_time.isoformat()
                })
                
                logger.info(f"Query executed successfully in {execution_time:.3f}s")
                return result
                
        except sqlite3.Error as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_code": "SQL_ERROR",
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
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN TRANSACTION")
            
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
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            schema_info = {
                "database_path": self.db_path,
                "tables": [],
                "total_tables": 0,
                "total_indexes": 0,
                "database_size_mb": 0,
                "oracle_compatibility": {
                    "foreign_keys_enabled": True,
                    "wal_mode": True,
                    "transaction_support": True
                }
            }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table information
                cursor.execute("""
                    SELECT name, type FROM sqlite_master 
                    WHERE type IN ('table', 'index') 
                    ORDER BY type, name
                """)
                
                objects = cursor.fetchall()
                
                for obj in objects:
                    if obj['type'] == 'table':
                        table_info = self._get_table_info(cursor, obj['name'])
                        schema_info["tables"].append(table_info)
                        schema_info["total_tables"] += 1
                    elif obj['type'] == 'index' and not obj['name'].startswith('sqlite_'):
                        schema_info["total_indexes"] += 1
                
                # Get database file size
                if os.path.exists(self.db_path):
                    size_bytes = os.path.getsize(self.db_path)
                    schema_info["database_size_mb"] = round(size_bytes / (1024 * 1024), 2)
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {"error": str(e)}
    
    def _get_table_info(self, cursor, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific table"""
        try:
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as row_count FROM {table_name}")
            row_count = cursor.fetchone()['row_count']
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            
            return {
                "table_name": table_name,
                "columns": [dict(col) for col in columns],
                "row_count": row_count,
                "indexes": [dict(idx) for idx in indexes],
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
