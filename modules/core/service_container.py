"""
Service container for dependency injection

This module provides a simple service container implementation for dependency injection.
"""

from typing import Dict, Any, Callable, Type, Optional, TypeVar, cast

T = TypeVar('T')

class ServiceContainer:
    """
    A simple service container for dependency injection
    
    This class provides a centralized registry for services and can
    automatically resolve dependencies when creating new instances.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[..., Any]] = {}
        
    def register(self, name: str, instance: Any) -> None:
        """
        Register an existing instance with the container
        
        Args:
            name: Name to register the service under
            instance: The service instance
        """
        self._services[name] = instance
        
    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """
        Register a factory function that will create the service when needed
        
        Args:
            name: Name to register the service under
            factory: Factory function that creates the service
        """
        self._factories[name] = factory
        
    def register_class(self, name: str, cls: Type[T], *args, **kwargs) -> None:
        """
        Register a class to be instantiated when the service is first requested
        
        Args:
            name: Name to register the service under
            cls: Class to instantiate
            *args: Positional arguments to pass to the constructor
            **kwargs: Keyword arguments to pass to the constructor
        """
        def factory():
            return cls(*args, **kwargs)
        
        self._factories[name] = factory
        
    def get(self, name: str) -> Any:
        """
        Get a service by name
        
        Args:
            name: Name of the service to retrieve
            
        Returns:
            The service instance
            
        Raises:
            KeyError: If the service is not registered
        """
        # Return existing instance if available
        if name in self._services:
            return self._services[name]
        
        # Check if we have a factory for this service
        if name in self._factories:
            # Create the instance and cache it
            instance = self._factories[name]()
            self._services[name] = instance
            return instance
        
        raise KeyError(f"Service '{name}' not registered")
        
    def get_typed(self, name: str, expected_type: Type[T]) -> T:
        """
        Get a service by name with type checking
        
        Args:
            name: Name of the service to retrieve
            expected_type: Expected type of the service
            
        Returns:
            The service instance with the correct type
            
        Raises:
            KeyError: If the service is not registered
            TypeError: If the service is not of the expected type
        """
        instance = self.get(name)
        
        if not isinstance(instance, expected_type):
            raise TypeError(f"Service '{name}' is not of type {expected_type.__name__}")
        
        return cast(T, instance)
    
    def has(self, name: str) -> bool:
        """
        Check if a service is registered
        
        Args:
            name: Name of the service to check
            
        Returns:
            True if the service is registered, False otherwise
        """
        return name in self._services or name in self._factories

# Global service container instance
container = ServiceContainer()

# Register core services (add more as needed)
def register_core_services() -> None:
    """Register core services with the container"""
    from modules.core.database import db_service
    
    # Register database service
    container.register('database', db_service)
    
    # You can register more services here as needed
    
# Initialize core services
register_core_services() 