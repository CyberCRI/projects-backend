# Load-testing for projects backend

## Setup

Open a shell in the load-testing directory and execute the following actions:

### Create a virtual environment

```bash
python3 -m venv .venv
```

### Activate the virtual environment

```bash
source .venv/bin/activate
```

### Install the required packages

```bash
pip install -r requirements.txt
```

## Configuration

- Choose the host and the number of users in the `locust.conf` file.
- Choose the tested endpoints in the `locustfile.py` file.


## Usage

### Retrieve the token

You need the client secret for the `projects-frontend-dev` Keycloak client.

Run the followin command :
```bash
CLIENT_SECRET=${CLIENT_SECRET} locust
```
Then click on the output link, this will open a browser window. Login, copy the url you have been redirected to, paste it in the terminal, and press enter.

You can now copy the token that has been displayed in the browser window (don't forget the equal signs at the end).

### Start locust using the token

Run the following command :
```bash
CLIENT_SECRET=${CLIENT_SECRET} TOKEN="${TOKEN}" locust
```

Then click on the link displayed in the terminal to open the locust web interface.

You can now run the tests.
