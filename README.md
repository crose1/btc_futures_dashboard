# Flask App Backend Project

The goal of this project is to showcase a simple implementation of the backend of a system which:

- receives a POST request in JSON format
- validates contents of the JSON
- performs mathematical operations on provided data
- returns result of operation, or error

Further, assume request takes following format:
```
request_JSON =  {"operation_type": "mean", "data": [1, 2, 3], "metadata": "free_text"}
```
This app could be extended to take different types of data e.g. csv as base64 in the data field or string of a list of numbers in metadata field.

# How to run the API
## Prerequisities 
1. `docker`  
2. `docker-compose`

## Start up Docker
This starts our container and runs tests on first run
```shell
docker compose up --build
```
Once the app is running, you can test it using the requests given in 'Test Requests' below
## Shut Down
```shell
docker compose down
```

# Test Requests
These requests can be run in a seperate terminal instance. 

#### For a mathematical operation
Simply edit the data field or the operation_type field to test different outputs or see error codes.
```shell
curl localhost:9000/operation -d '{"operation_type": "mean", "data": [1, 200, 3], "metadata": "free_text"}' -H 'Content-Type: application/json' -X POST
```
This request should return an error as we have a string in the data field
```shell 
curl localhost:9000/operation -d '{"operation_type": "mean", "data": [1, "200", 3], "metadata": "free_text"}' -H 'Content-Type: application/json' -X POST
```

#### For a health check 
```shell
curl localhost:9000/healthcheck -X  GET
```
This can also be tested by going to localhost:9000/healthcheck in your browser



## Testing locally - This will only work on MacOS, not recommended on Windows
1. `pip install pipenv`
2. `cd backend_implementation` 
3. `pipenv --python 3.9` #Creates Python 3.9 virtual env
4. `pipenv install -r requirements.txt` #Installs all dependencies 
5. `pipenv shell` #Activates virtual env
6. `pytest ` #Runs all tests on app - will fail on Windows

## Prerequisities
1. Local Python interpreter



