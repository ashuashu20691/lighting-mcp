"""
Oracle Database Connection Module
Real Oracle ADB connection implementation with wallet authentication
"""

import os
import cx_Oracle
import oracledb
from typing import Dict, Any, Optional, List
import logging
from contextlib import contextmanager
import json
from datetime import datetime

class OracleADBConnection:
    """
    Oracle Autonomous Database (ADB) Connection Manager
    Handles secure connections using Oracle Wallet authentication
    """
    
    def __init__(self, 
                 wallet_location: str = None,
                 wallet_password: str = None,
                 connection_string: str = None,
                 username: str = None,
                 password: str = None):
        """
        Initialize Oracle ADB connection
        
        Args:
            wallet_location: Path to Oracle Wallet directory
            wallet_password: Wallet password 
            connection_string: TNS connection string or service name
            username: Database username
            password: Database password
        """
        self.wallet_location = wallet_location or os.getenv('ORACLE_WALLET_LOCATION')
        self.wallet_password = wallet_password or os.getenv('ORACLE_WALLET_PASSWORD')
        self.connection_string = connection_string or os.getenv('ORACLE_CONNECTION_STRING')
        self.username = username or os.getenv('ORACLE_USERNAME')
        self.password = password or os.getenv('ORACLE_PASSWORD')
        
        self.connection_pool = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize Oracle client
        self._initialize_oracle_client()
    
    def _initialize_oracle_client(self):
        """Initialize Oracle client with wallet configuration"""
        try:
            # Use python-oracledb (new Oracle Python driver)
            oracledb.init_oracle_client()
            
            if self.wallet_location:
                # Configure wallet location
                os.environ['TNS_ADMIN'] = self.wallet_location
                self.logger.info(f"Oracle wallet configured at: {self.wallet_location}")
            
        except Exception as e:
            self.logger.warning(f"Oracle client initialization: {e}")
            # Fallback to cx_Oracle if available
            try:
                if self.wallet_location:
                    cx_Oracle.init_oracle_client(config_dir=self.wallet_location)
                    self.logger.info("Using cx_Oracle with wallet")
            except Exception as cx_error:
                self.logger.error(f"Failed to initialize Oracle client: {cx_error}")
    
    def create_connection_pool(self, 
                              min_connections: int = 1,
                              max_connections: int = 5,
                              increment: int = 1) -> bool:
        """
        Create Oracle connection pool for better performance
        
        Args:
            min_connections: Minimum pool connections
            max_connections: Maximum pool connections
            increment: Connection increment
            
        Returns:
            bool: Success status
        """
        try:
            # Connection parameters
            connect_params = {
                'user': self.username,
                'password': self.password,
                'dsn': self.connection_string,
                'min': min_connections,
                'max': max_connections,
                'increment': increment,
                'threaded': True
            }
            
            # Create connection pool
            self.connection_pool = oracledb.create_pool(**connect_params)
            self.logger.info(f"Oracle connection pool created: {min_connections}-{max_connections} connections")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create connection pool: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for Oracle database connections
        Automatically handles connection cleanup
        
        Usage:
            with oracle_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM employees")
                results = cursor.fetchall()
        """
        connection = None
        try:
            if self.connection_pool:
                connection = self.connection_pool.acquire()
            else:
                # Direct connection if no pool
                connection = oracledb.connect(
                    user=self.username,
                    password=self.password,
                    dsn=self.connection_string
                )
            
            yield connection
            
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                if self.connection_pool:
                    self.connection_pool.release(connection)
                else:
                    connection.close()
    
    def execute_query(self, 
                     query: str, 
                     parameters: Optional[Dict[str, Any]] = None,
                     fetch_mode: str = 'all') -> Dict[str, Any]:
        """
        Execute SQL query with parameters
        
        Args:
            query: SQL query string
            parameters: Query parameters dictionary
            fetch_mode: 'all', 'one', 'many', or 'none'
            
        Returns:
            Dict containing query results and metadata
        """
        start_time = datetime.now()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute query with parameters
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                # Fetch results based on mode
                if fetch_mode == 'all':
                    rows = cursor.fetchall()
                elif fetch_mode == 'one':
                    rows = cursor.fetchone()
                elif fetch_mode == 'many':
                    rows = cursor.fetchmany()
                else:
                    rows = None
                    conn.commit()  # For INSERT/UPDATE/DELETE
                
                # Get column information
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Format results
                if rows and fetch_mode in ['all', 'many']:
                    data = [dict(zip(columns, row)) for row in rows]
                elif rows and fetch_mode == 'one':
                    data = dict(zip(columns, rows))
                else:
                    data = []
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'status': 'success',
                    'data': data,
                    'columns': columns,
                    'row_count': len(data) if isinstance(data, list) else (1 if data else 0),
                    'execution_time': execution_time,
                    'query': query,
                    'parameters': parameters
                }
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Query execution failed: {e}")
            
            return {
                'status': 'error',
                'error_message': str(e),
                'error_type': type(e).__name__,
                'execution_time': execution_time,
                'query': query,
                'parameters': parameters
            }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get comprehensive database schema information
        
        Returns:
            Dict containing tables, views, and schema metadata
        """
        try:
            schema_info = {
                'tables': [],
                'views': [],
                'sequences': [],
                'indexes': [],
                'metadata': {}
            }
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("""
                    SELECT table_name, tablespace_name, num_rows, last_analyzed
                    FROM user_tables
                    ORDER BY table_name
                """)
                schema_info['tables'] = [
                    {
                        'name': row[0],
                        'tablespace': row[1],
                        'rows': row[2],
                        'analyzed': row[3].isoformat() if row[3] else None
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get views
                cursor.execute("""
                    SELECT view_name, text_length
                    FROM user_views
                    ORDER BY view_name
                """)
                schema_info['views'] = [
                    {'name': row[0], 'text_length': row[1]}
                    for row in cursor.fetchall()
                ]
                
                # Get sequences
                cursor.execute("""
                    SELECT sequence_name, min_value, max_value, increment_by, last_number
                    FROM user_sequences
                    ORDER BY sequence_name
                """)
                schema_info['sequences'] = [
                    {
                        'name': row[0],
                        'min_value': row[1],
                        'max_value': row[2],
                        'increment': row[3],
                        'last_number': row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get database metadata
                cursor.execute("SELECT * FROM v$version WHERE rownum = 1")
                version_info = cursor.fetchone()
                schema_info['metadata']['version'] = version_info[0] if version_info else 'Unknown'
                
                cursor.execute("SELECT username FROM user_users")
                user_info = cursor.fetchone()
                schema_info['metadata']['username'] = user_info[0] if user_info else 'Unknown'
                
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Failed to get schema info: {e}")
            return {'error': str(e)}
    
    def get_table_details(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict containing table structure and constraints
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get column information
                cursor.execute("""
                    SELECT column_name, data_type, data_length, data_precision, 
                           data_scale, nullable, data_default
                    FROM user_tab_columns
                    WHERE table_name = :table_name
                    ORDER BY column_id
                """, {'table_name': table_name.upper()})
                
                columns = [
                    {
                        'name': row[0],
                        'type': row[1],
                        'length': row[2],
                        'precision': row[3],
                        'scale': row[4],
                        'nullable': row[5] == 'Y',
                        'default': row[6]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get constraints
                cursor.execute("""
                    SELECT constraint_name, constraint_type, search_condition
                    FROM user_constraints
                    WHERE table_name = :table_name
                """, {'table_name': table_name.upper()})
                
                constraints = [
                    {
                        'name': row[0],
                        'type': row[1],
                        'condition': row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'constraints': constraints
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get table details for {table_name}: {e}")
            return {'error': str(e)}
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Oracle database connection
        
        Returns:
            Dict containing connection test results
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM dual")
                result = cursor.fetchone()
                
                # Get additional connection info
                cursor.execute("SELECT user, sysdate FROM dual")
                user_info = cursor.fetchone()
                
                return {
                    'status': 'success',
                    'connected': True,
                    'user': user_info[0],
                    'server_time': user_info[1].isoformat(),
                    'test_query_result': result[0]
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'error': str(e)
            }
    
    def close_pool(self):
        """Close connection pool and cleanup resources"""
        if self.connection_pool:
            self.connection_pool.close()
            self.logger.info("Oracle connection pool closed")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close_pool()


# Example usage and configuration
def create_oracle_connection_from_env() -> OracleADBConnection:
    """
    Create Oracle connection using environment variables
    
    Required environment variables:
    - ORACLE_WALLET_LOCATION: Path to wallet directory
    - ORACLE_WALLET_PASSWORD: Wallet password
    - ORACLE_CONNECTION_STRING: Database connection string
    - ORACLE_USERNAME: Database username
    - ORACLE_PASSWORD: Database password
    
    Returns:
        OracleADBConnection instance
    """
    return OracleADBConnection()


def create_oracle_connection_from_config(config_file: str) -> OracleADBConnection:
    """
    Create Oracle connection from JSON configuration file
    
    Args:
        config_file: Path to JSON configuration file
        
    Example config.json:
    {
        "wallet_location": "/path/to/wallet",
        "wallet_password": "wallet_password",
        "connection_string": "service_name_high",
        "username": "ADMIN",
        "password": "database_password"
    }
    
    Returns:
        OracleADBConnection instance
    """
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    return OracleADBConnection(**config)


# Connection validation
def validate_oracle_setup() -> Dict[str, Any]:
    """
    Validate Oracle client and connection setup
    
    Returns:
        Dict containing validation results
    """
    validation_results = {
        'oracle_client': False,
        'wallet_location': False,
        'environment_vars': False,
        'connection_test': False,
        'errors': []
    }
    
    try:
        # Check Oracle client
        import oracledb
        validation_results['oracle_client'] = True
    except ImportError:
        validation_results['errors'].append("python-oracledb not installed")
    
    # Check wallet location
    wallet_location = os.getenv('ORACLE_WALLET_LOCATION')
    if wallet_location and os.path.exists(wallet_location):
        validation_results['wallet_location'] = True
    else:
        validation_results['errors'].append("ORACLE_WALLET_LOCATION not set or path doesn't exist")
    
    # Check required environment variables
    required_vars = [
        'ORACLE_WALLET_LOCATION',
        'ORACLE_WALLET_PASSWORD', 
        'ORACLE_CONNECTION_STRING',
        'ORACLE_USERNAME',
        'ORACLE_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if not missing_vars:
        validation_results['environment_vars'] = True
    else:
        validation_results['errors'].append(f"Missing environment variables: {missing_vars}")
    
    # Test connection if environment is set up
    if validation_results['oracle_client'] and validation_results['environment_vars']:
        try:
            oracle_conn = create_oracle_connection_from_env()
            test_result = oracle_conn.test_connection()
            validation_results['connection_test'] = test_result.get('connected', False)
            if not validation_results['connection_test']:
                validation_results['errors'].append(f"Connection test failed: {test_result.get('error')}")
        except Exception as e:
            validation_results['errors'].append(f"Connection test error: {e}")
    
    return validation_results


if __name__ == "__main__":
    # Example usage
    print("Oracle ADB Connection Module")
    print("Validating setup...")
    
    validation = validate_oracle_setup()
    print(json.dumps(validation, indent=2))
    
    if all([validation['oracle_client'], validation['environment_vars']]):
        print("\nTesting connection...")
        oracle_db = create_oracle_connection_from_env()
        test_result = oracle_db.test_connection()
        print(json.dumps(test_result, indent=2, default=str))