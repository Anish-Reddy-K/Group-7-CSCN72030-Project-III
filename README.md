# FriendLens Web App

## Features
- **Home Page (/):** Displays a collection of 4K wallpapers from the specified directory.
- **Feed Page (/feed):** Renders a feed page (placeholder) for future functionality.

## Requirements
- Python 3.x
- Flask

## Installation
1. Clone the repository to your local machine:
    ```bash
    git clone https://github.com/your-username/FriendLens.git
    ```

2. Navigate to the project directory:
    ```bash
    cd FriendLens
    ```

3. Install the required dependencies:
    ```bash
    pip install Flask
    ```

## Usage
1. Update the `directory` variable in the `app.py` file to point to your desired directory containing the 4K wallpapers.

    ```python
    directory = 'C:\\path\\to\\your\\wallpapers'
    ```

2. Run the application:
    ```bash
    python app.py
    ```

3. Open a web browser and go to [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to access the home page or [http://127.0.0.1:5000/feed](http://127.0.0.1:5000/feed) for the feed page.

## Configuration
- **Debug Mode:** The application is set to run in debug mode for development purposes. Change the `debug` parameter to `False` in the `app.run()` statement if deploying in a production environment.

```python
if __name__ == '__main__':
    app.run(debug=True)
