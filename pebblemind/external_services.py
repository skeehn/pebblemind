"""External Services Integration for PebbleMind"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import sqlite3

try:
    import aiohttp
except ImportError:
    aiohttp = None


class ExternalServiceConnector:
    """Connects to various external services and databases"""
    
    def __init__(self):
        self.active_connections = {}
        self.service_configs = {}
    
    async def connect_to_database(self, 
                                db_type: str, 
                                connection_string: str) -> Dict[str, Any]:
        """Connect to an external database"""
        try:
            if db_type.lower() == "sqlite":
                # For SQLite, just verify the file exists
                db_path = Path(connection_string)
                if not db_path.exists():
                    return {
                        "status": "error",
                        "error": f"SQLite file does not exist: {connection_string}"
                    }
                
                # Test the connection
                conn = sqlite3.connect(connection_string)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                
                self.active_connections["sqlite"] = connection_string
                return {
                    "status": "success",
                    "connection_type": "sqlite",
                    "path": str(db_path),
                    "message": f"Connected to SQLite database at {connection_string}"
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Database type {db_type} not supported. Supported: sqlite"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def query_database(self, 
                           db_type: str, 
                           query: str, 
                           connection_string: str = None) -> Dict[str, Any]:
        """Query an external database"""
        try:
            if db_type.lower() == "sqlite":
                # If connection_string is not provided, use stored connection
                if not connection_string and "sqlite" in self.active_connections:
                    connection_string = self.active_connections["sqlite"]
                
                if not connection_string:
                    return {
                        "status": "error",
                        "error": "No SQLite connection available"
                    }
                
                # Execute the query
                conn = sqlite3.connect(connection_string)
                cursor = conn.cursor()
                cursor.execute(query)
                
                # Get column names and rows
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                conn.close()
                
                return {
                    "status": "success",
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows],
                    "row_count": len(rows)
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Database type {db_type} not supported"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def call_rest_api(self, 
                          url: str, 
                          method: str = "GET",
                          headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None,
                          data: Optional[Union[Dict[str, Any], str]] = None) -> Dict[str, Any]:
        """Make a call to a REST API"""
        try:
            if aiohttp is None:
                raise ImportError("aiohttp is required for REST API integrations")
            if headers is None:
                headers = {}
            
            # Add default headers
            headers["User-Agent"] = "PebbleMind/1.0"
            headers["Accept"] = "application/json"
            
            async with aiohttp.ClientSession() as session:
                # Prepare the request based on method
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        result_data = await response.text()
                        
                elif method.upper() == "POST":
                    # Determine content type
                    if isinstance(data, dict):
                        async with session.post(url, headers=headers, json=data) as response:
                            result_data = await response.text()
                    else:
                        headers["Content-Type"] = "application/json"
                        async with session.post(url, headers=headers, data=data) as response:
                            result_data = await response.text()
                
                elif method.upper() == "PUT":
                    if isinstance(data, dict):
                        async with session.put(url, headers=headers, json=data) as response:
                            result_data = await response.text()
                    else:
                        headers["Content-Type"] = "application/json"
                        async with session.put(url, headers=headers, data=data) as response:
                            result_data = await response.text()
                
                elif method.upper() == "DELETE":
                    async with session.delete(url, headers=headers) as response:
                        result_data = await response.text()
                
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP method {method} not supported. Use GET, POST, PUT, DELETE"
                    }
                
                # Try to parse JSON response
                try:
                    parsed_data = json.loads(result_data)
                    json_response = True
                except json.JSONDecodeError:
                    parsed_data = result_data
                    json_response = False
                
                return {
                    "status": "success",
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": parsed_data,
                    "is_json": json_response,
                    "url": url,
                    "method": method
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "url": url,
                "method": method
            }
    
    async def connect_to_weather_service(self, api_key: str) -> Dict[str, Any]:
        """Connect to a weather service (OpenWeatherMap as example)"""
        try:
            if aiohttp is None:
                raise ImportError("aiohttp is required for weather service integrations")
            # Test the API key by making a simple request
            url = f"http://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}&units=metric"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        self.service_configs["weather"] = {"api_key": api_key}
                        return {
                            "status": "success",
                            "service": "weather",
                            "message": "Successfully connected to weather service"
                        }
                    else:
                        return {
                            "status": "error",
                            "service": "weather",
                            "error": f"Weather service returned status {response.status}"
                        }
        
        except Exception as e:
            return {
                "status": "error",
                "service": "weather",
                "error": str(e)
            }
    
    async def get_weather_data(self, location: str) -> Dict[str, Any]:
        """Get weather data from connected weather service"""
        if "weather" not in self.service_configs:
            return {
                "status": "error",
                "error": "Weather service not connected. Call connect_to_weather_service first."
            }
        
        try:
            if aiohttp is None:
                raise ImportError("aiohttp is required for weather service integrations")
            api_key = self.service_configs["weather"]["api_key"]
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract relevant weather information
                        weather_info = {
                            "location": data["name"],
                            "country": data["sys"]["country"],
                            "temperature": data["main"]["temp"],
                            "feels_like": data["main"]["feels_like"],
                            "humidity": data["main"]["humidity"],
                            "pressure": data["main"]["pressure"],
                            "description": data["weather"][0]["description"],
                            "wind_speed": data["wind"]["speed"],
                        }
                        
                        return {
                            "status": "success",
                            "service": "weather",
                            "data": weather_info
                        }
                    else:
                        return {
                            "status": "error",
                            "service": "weather",
                            "error": f"Weather service returned status {response.status}"
                        }
        
        except Exception as e:
            return {
                "status": "error",
                "service": "weather",
                "error": str(e)
            }
    
    def get_connected_services(self) -> List[str]:
        """Get list of connected services"""
        return list(self.active_connections.keys()) + list(self.service_configs.keys())
    
    async def disconnect_all(self):
        """Disconnect from all services"""
        self.active_connections.clear()
        self.service_configs.clear()


class ServiceIntegrationManager:
    """Manages integration with external services for PebbleMind"""
    
    def __init__(self):
        self.service_connector = ExternalServiceConnector()
        self.integration_history = []
    
    async def integrate_with_service(self, 
                                   service_type: str, 
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate with a specified external service"""
        if service_type.lower() == "database":
            db_type = config.get("type", "sqlite")
            connection_string = config.get("connection_string")
            
            if not connection_string:
                return {
                    "status": "error",
                    "error": "connection_string is required for database integration"
                }
            
            result = await self.service_connector.connect_to_database(db_type, connection_string)
        
        elif service_type.lower() == "rest_api":
            url = config.get("url")
            method = config.get("method", "GET")
            headers = config.get("headers", {})
            params = config.get("params", {})
            data = config.get("data", {})
            
            if not url:
                return {
                    "status": "error",
                    "error": "url is required for REST API integration"
                }
            
            result = await self.service_connector.call_rest_api(url, method, headers, params, data)
        
        elif service_type.lower() == "weather":
            api_key = config.get("api_key")
            
            if not api_key:
                return {
                    "status": "error",
                    "error": "api_key is required for weather service integration"
                }
            
            result = await self.service_connector.connect_to_weather_service(api_key)
        
        else:
            return {
                "status": "error",
                "error": f"Service type '{service_type}' not supported. "
                        f"Supported: database, rest_api, weather"
            }
        
        # Add to integration history
        self.integration_history.append({
            "service_type": service_type,
            "config": config,
            "result": result,
            "timestamp": time.monotonic()
        })
        
        return result
    
    async def execute_external_query(self, 
                                   query_type: str,
                                   **kwargs) -> Dict[str, Any]:
        """Execute a query on an external service"""
        if query_type.lower() == "database_query":
            db_type = kwargs.get("db_type", "sqlite")
            query = kwargs.get("query")
            connection_string = kwargs.get("connection_string")
            
            if not query:
                return {
                    "status": "error",
                    "error": "query is required for database queries"
                }
            
            return await self.service_connector.query_database(db_type, query, connection_string)
        
        elif query_type.lower() == "rest_call":
            url = kwargs.get("url")
            method = kwargs.get("method", "GET")
            headers = kwargs.get("headers", {})
            params = kwargs.get("params", {})
            data = kwargs.get("data", {})
            
            if not url:
                return {
                    "status": "error",
                    "error": "url is required for REST calls"
                }
            
            return await self.service_connector.call_rest_api(url, method, headers, params, data)
        
        elif query_type.lower() == "weather_data":
            location = kwargs.get("location")
            
            if not location:
                return {
                    "status": "error",
                    "error": "location is required for weather data"
                }
            
            return await self.service_connector.get_weather_data(location)
        
        else:
            return {
                "status": "error",
                "error": f"Query type '{query_type}' not supported. "
                        f"Supported: database_query, rest_call, weather_data"
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        return {
            "connected_services": self.service_connector.get_connected_services(),
            "integration_count": len(self.integration_history),
            "history": self.integration_history[-5:]  # Last 5 integrations
        }


# Example usage functions that could be integrated into PebbleMind
async def execute_external_task(task: str, 
                              service_manager: ServiceIntegrationManager,
                              config: Dict[str, Any]) -> str:
    """Execute an external service task based on the task description"""
    # Simple keyword matching to determine the type of external task
    task_lower = task.lower()
    
    if "database" in task_lower or "sql" in task_lower:
        query = task.replace("database", "").replace("sql", "").strip()
        if query:
            result = await service_manager.execute_external_query(
                "database_query",
                db_type=config.get("db_type", "sqlite"),
                query=query,
                connection_string=config.get("connection_string")
            )
            return f"Database result: {result}"
        else:
            return "Please specify a database query to execute"
    
    elif "weather" in task_lower:
        location = config.get("location", "New York")
        result = await service_manager.execute_external_query(
            "weather_data",
            location=location
        )
        return f"Weather result: {result}"
    
    elif "api" in task_lower or "http" in task_lower:
        url = config.get("url")
        if url:
            result = await service_manager.execute_external_query(
                "rest_call",
                url=url,
                method=config.get("method", "GET"),
                headers=config.get("headers", {}),
                data=config.get("data", {})
            )
            return f"API result: {result}"
        else:
            return "URL not provided for API call"
    
    else:
        return f"External task not recognized: {task}"
