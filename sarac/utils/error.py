"""
Enhanced error handling and reporting system for Sarac compiler.

Features:
- Error collection (multiple errors)
- Detailed error messages with context
- Warning system
- Error codes for programmatic handling
- Suggestions for common mistakes
"""

import sys
from typing import Optional, List, Dict


class ErrorInfo:
    """Represents a single error with full context."""
    
    ERROR_CODES = {
        'E0001': 'syntax error',
        'E0002': 'lexical error',
        'E0003': 'name error',
        'E0004': 'type error',
        'E0005': 'semantic error',
    }
    
    def __init__(self, code, category, message, line=None, column=None, 
                 context=None, expected=None, suggestion=None):
        self.code = code
        self.category = category
        self.message = message
        self.line = line
        self.column = column
        self.context = context  # Source code context around error
        self.expected = expected  # What was expected
        self.suggestion = suggestion  # Suggestion to fix
    
    def format(self, show_context=True):
        """Format error message with full context."""
        parts = []
        
        # Error code and category
        parts.append(f"{self.code}: {self.category}: {self.message}")
        
        # Location
        if self.line is not None:
            if self.column is not None:
                parts.append(f"at line {self.line}, column {self.column}")
            else:
                parts.append(f"at line {self.line}")
        
        # Context line
        if show_context and self.context:
            parts.append(f"context: {self.context}")
        
        # Expected
        if self.expected:
            parts.append(f"expected: {self.expected}")
        
        # Suggestion
        if self.suggestion:
            parts.append(f"suggestion: {self.suggestion}")
        
        return "\n  ".join(parts)


class WarningInfo:
    """Represents a single warning."""
    
    WARNING_CODES = {
        'W0001': 'unused variable',
        'W0002': 'unreachable code',
        'W0003': 'implicit conversion',
        'W0004': 'unused function',
        'W0005': 'missing return',
    }
    
    def __init__(self, code, message, line=None, column=None, context=None):
        self.code = code
        self.message = message
        self.line = line
        self.column = column
        self.context = context
    
    def format(self):
        """Format warning message."""
        parts = [f"{self.code}: warning: {self.message}"]
        if self.line is not None:
            if self.column is not None:
                parts.append(f"at line {self.line}, column {self.column}")
            else:
                parts.append(f"at line {self.line}")
        if self.context:
            parts.append(f"context: {self.context}")
        return "\n  ".join(parts)


class ErrorCollector:
    """Collects errors and warnings during compilation."""
    
    def __init__(self, max_errors=50, warnings_as_errors=False, 
                 suppress_warnings=False):
        self.errors: List[ErrorInfo] = []
        self.warnings: List[WarningInfo] = []
        self.max_errors = max_errors
        self.warnings_as_errors = warnings_as_errors
        self.suppress_warnings = suppress_warnings
        self.source_lines: List[str] = []
    
    def set_source(self, source_code: str):
        """Set source code for context extraction."""
        self.source_lines = source_code.split('\n')
    
    def get_context(self, line: int, column: int = None, context_lines: int = 1) -> Optional[str]:
        """Extract context around error location."""
        if not self.source_lines or line < 1 or line > len(self.source_lines):
            return None
        
        # Get the line with error
        error_line = self.source_lines[line - 1]
        
        # Add pointer if column is specified
        if column is not None and column > 0:
            pointer = " " * (column - 1) + "^"
            return f"{error_line}\n{pointer}"
        
        return error_line
    
    def add_error(self, code: str, category: str, message: str, 
                  line: Optional[int] = None, column: Optional[int] = None,
                  expected: Optional[str] = None, suggestion: Optional[str] = None):
        """Add an error to the collection."""
        if len(self.errors) >= self.max_errors:
            return
        
        context = self.get_context(line, column) if line else None
        error = ErrorInfo(code, category, message, line, column, context, 
                         expected, suggestion)
        self.errors.append(error)
    
    def add_warning(self, code: str, message: str, 
                   line: Optional[int] = None, column: Optional[int] = None):
        """Add a warning to the collection."""
        if self.suppress_warnings:
            return
        
        # Check if this warning type should be enabled
        # Map warning codes to flag names
        code_to_flag = {
            'W0001': 'unused',
            'W0002': 'unreachable',
            'W0003': 'conversion',
            'W0004': 'unused',  # unused function
            'W0005': 'unreachable',  # missing return
        }
        
        flag_name = code_to_flag.get(code)
        
        # If specific flags are set, only show warnings for those flags
        # If 'all' is set, show all warnings
        if hasattr(self, '_warning_flags') and self._warning_flags:
            if 'all' not in self._warning_flags:
                if flag_name and flag_name not in self._warning_flags:
                    return  # This warning type is not enabled
        
        context = self.get_context(line, column) if line else None
        warning = WarningInfo(code, message, line, column, context)
        self.warnings.append(warning)
        
        if self.warnings_as_errors:
            self.add_error('E0005', 'semantic error', 
                          f"warning treated as error: {message}", 
                          line, column)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def print_all(self):
        """Print all errors and warnings."""
        # Print errors
        for i, error in enumerate(self.errors, 1):
            print(f"error {i}: {error.format()}", file=sys.stderr)
        
        # Print warnings
        if not self.suppress_warnings:
            for i, warning in enumerate(self.warnings, 1):
                print(f"warning {i}: {warning.format()}", file=sys.stderr)
    
    def get_summary(self) -> str:
        """Get summary of errors and warnings."""
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        
        parts = []
        if error_count > 0:
            parts.append(f"{error_count} error(s)")
        if warning_count > 0:
            parts.append(f"{warning_count} warning(s)")
        
        if parts:
            return "compilation failed with " + ", ".join(parts)
        return "compilation successful"
    
    def raise_if_errors(self):
        """Raise exception if there are errors."""
        if self.has_errors():
            self.print_all()
            raise SaraErrorException(self.get_summary())


# Global error collector instance
_collector = None


def set_error_collector(collector: ErrorCollector):
    """Set the global error collector."""
    global _collector
    _collector = collector


def get_error_collector() -> ErrorCollector:
    """Get the global error collector."""
    global _collector
    if _collector is None:
        _collector = ErrorCollector()
        _collector._collect_mode = False  # Immediate mode by default
    return _collector


def error(func):
    """Decorator for error reporting (backward compatible)."""
    def error_wrapper(cls, msg, line=None, column=None, 
                     expected=None, suggestion=None, code=None):
        Error.errors += 1
        
        # Try to get collector, but don't fail if not available
        try:
            collector = get_error_collector()
            
            # Determine error code and category
            if code is None:
                if 'syntax' in func.__name__:
                    code = 'E0001'
                    category = 'syntax error'
                elif 'lexical' in func.__name__:
                    code = 'E0002'
                    category = 'lexical error'
                elif 'name' in func.__name__:
                    code = 'E0003'
                    category = 'name error'
                elif 'type' in func.__name__:
                    code = 'E0004'
                    category = 'type error'
                else:
                    code = 'E0005'
                    category = 'semantic error'
            else:
                category = ErrorInfo.ERROR_CODES.get(code, 'error')
            
            # Add error to collector
            collector.add_error(code, category, msg, line, column, expected, suggestion)
            
            # Format message for backward compatibility
            if line is None:
                error_msg = func(cls, msg)
            else:
                error_msg = func(cls, msg, line, column)
            
            # Print formatted message (backward compatible)
            print(error_msg, file=sys.stderr)
            
            # For backward compatibility: if collector is in immediate mode, raise
            # Otherwise, errors are collected and reported at the end
            if not hasattr(collector, '_collect_mode') or not collector._collect_mode:
                raise SaraErrorException(error_msg)
            
            return error_msg
        except (NameError, AttributeError):
            # Fallback if collector not available
            if line is None:
                error_msg = func(cls, msg)
            else:
                error_msg = func(cls, msg, line, column)
            print(error_msg, file=sys.stderr)
            raise SaraErrorException(error_msg)
    return error_wrapper


class SaraErrorException(Exception):
    """Exception raised when compilation errors occur."""
    pass


class Error(object):
    """Error reporting class (backward compatible interface)."""
    errors = 0

    @classmethod
    @error
    def syntax_error(cls, msg, line=None, column=None, expected=None, suggestion=None):
        """Report a syntax error."""
        Error.errors += 1
        if line is None:
            return f"syntax error: {msg}"
        return f"syntax error: {msg}"

    @classmethod
    @error
    def name_error(cls, msg, line, column, expected=None, suggestion=None):
        """Report a name resolution error."""
        Error.errors += 1
        return f"name error: {msg}"

    @classmethod
    @error
    def lexical_error(cls, msg, line, column, expected=None, suggestion=None):
        """Report a lexical analysis error."""
        Error.errors += 1
        return f"lexical error: {msg}"

    @classmethod
    @error
    def type_error(cls, msg, line, column, expected=None, suggestion=None):
        """Report a type checking error."""
        Error.errors += 1
        return f"type error: {msg}"


class Warning(object):
    """Warning reporting class."""
    
    @classmethod
    def unused_variable(cls, var_name, line, column):
        """Warn about unused variable."""
        collector = get_error_collector()
        collector.add_warning('W0001', f"unused variable '{var_name}'", line, column)
    
    @classmethod
    def unreachable_code(cls, line, column):
        """Warn about unreachable code."""
        collector = get_error_collector()
        collector.add_warning('W0002', "unreachable code", line, column)
    
    @classmethod
    def implicit_conversion(cls, from_type, to_type, line, column):
        """Warn about implicit type conversion."""
        collector = get_error_collector()
        collector.add_warning('W0003', 
                           f"implicit conversion from '{from_type}' to '{to_type}'", 
                           line, column)
    
    @classmethod
    def unused_function(cls, func_name, line, column):
        """Warn about unused function."""
        collector = get_error_collector()
        collector.add_warning('W0004', f"unused function '{func_name}'", line, column)
    
    @classmethod
    def missing_return(cls, func_name, line, column):
        """Warn about missing return statement."""
        collector = get_error_collector()
        collector.add_warning('W0005', 
                           f"function '{func_name}' may not return a value", 
                           line, column)
