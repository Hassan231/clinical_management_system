# Entry point for the Clinical Management System application.
# Run this file directly to start the Flask development server.

from app import create_app  # Import the application factory function from the app package

app = create_app()  # Call the factory to build and configure the Flask app instance


if __name__ == "__main__":
    # Only start the dev server when this script is run directly (not when imported as a module)
    app.run(debug=True)  # debug=True enables auto-reload on code changes and detailed error pages
