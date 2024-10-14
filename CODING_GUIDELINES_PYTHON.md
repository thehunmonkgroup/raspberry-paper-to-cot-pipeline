1. Always encapsulate the core functionality of the script into a class.

2. Use type hints consistently throughout the code -- if any type hints in existing code are wrong or missing, fix them.

3. Include a clear, concise module-level docstring explaining the script's purpose.

4. Implement command-line argument parsing using the argparse module. When defining arguments:
   * Always include a --debug argument that activates debug logging.
   * Order arguments logically: more important or required arguments first, followed by optional ones.
   * Group related arguments together.
   * Maintain the same order of arguments in the argparse definition and when passing them to methods/functions.

5. Utilize the logging module or a provided logging class or setup method for consistent and configurable logging output. Use detailed logging throughout the script:
   * Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) based on the importance of the log message.
   * Include DEBUG level logs to show detailed progress of the script's execution.

6. Implement proper exception handling with try-except blocks where appropriate.

7. Use the pathlib module for file and directory operations.

8. Use clear, descriptive names for all functions, methods, and variables.

9. Separate concerns by breaking down functionality into distinct methods or functions. If any existing methods or functions do not follow best practices in this regard, fix them by breaking them down into distinct methods or functions.

10. Use f-strings for string formatting. If any existing strings do not use f-strings and can be easily fixed, fixed them.

11. Define constants and default values clearly, preferably at the module or class level. If you find existing hard-coded values that would be more appropriate as a constant, fix them.

12. Include a main guard (if __name__ == "__main__":) to control script execution.

13. Use appropriate exit codes to indicate script success or failure.

14. Employ the subprocess module for executing system commands when necessary.

15. Adhere to PEP 8 guidelines for code style and formatting.

16. Document all functions, methods, and classes using reStructuredText format compatible with Sphinx, including descriptions, parameters, return values, and any relevant examples or notes.
