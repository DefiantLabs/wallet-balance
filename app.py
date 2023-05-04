import toml
import requests
import psycopg2

# Load the configuration file
config = toml.load("config.toml")

# Set up the Slack webhook URL
webhook_url = config["slack"]["webhook_url"]

# Set up the RPC servers for each blockchain
rpc_servers = config["blockchains"]

# Set up the database connection
db_config = config["database"]


# Define a function to check if an account exists on a blockchain
def account_exists(blockchain, address):
    rpc_server = rpc_servers[blockchain]
    response = requests.get(rpc_server + "/auth/accounts/" + address)
    print(response)
    return response.status_code == 200


# Define a function to save a wallet address to the remote database
def save_wallet(user_id, wallet_address):
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["username"],
            password=db_config["password"]
        )
        cur = conn.cursor()

        # Check if the "wallets" table exists; create it if it does not
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'wallets')")
        if not cur.fetchone()[0]:
            cur.execute(
                "CREATE TABLE wallets (id SERIAL PRIMARY KEY, user_id VARCHAR(255) NOT NULL, wallet_address VARCHAR(255) NOT NULL)"
            )
            conn.commit()
            print("Created wallets table")

        # Insert the wallet address and username into the "wallets" table
        cur.execute(
            "INSERT INTO wallets (user_id, wallet_address) VALUES (%s, %s)",
            (user_id, wallet_address)
        )
        conn.commit()
        print(f"Saved wallet {wallet_address} for user {user_id}")

    except Exception as e:
        print("Error saving wallet to database:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()


# Define a function to handle the "!save" command
def handle_save_command(command, username):
    tokens = command.split()
    print(len(tokens))
    if len(tokens) != 2:
        # print("Invalid command: expected '!save address'")
        return "Invalid command: expected '!save address'"
    address = tokens[1]
    # Check if the address is valid for any of the supported blockchains
    valid_address = False
    for blockchain in rpc_servers:
        print(account_exists(blockchain, address))
        if account_exists(blockchain, address):
            valid_address = True
            break
    if not valid_address:
        return "Invalid address: address not found on any supported blockchain"
    # Save the wallet to the remote database and the local wallet dictionary
    save_wallet(username, address)
    return "Wallet {} saved for user {}".format(address, username)


# Define a function to handle the "!show wallets" command
def handle_show_wallets_command(username):
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["username"],
            password=db_config["password"]
        )
        cur = conn.cursor()

        # Retrieve all wallets for the user from the database
        cur.execute(
            "SELECT wallet_address FROM wallets WHERE user_id = %s",
            (username,)
        )
        rows = cur.fetchall()
        wallets = [row[0] for row in rows]

        if wallets:
            return "Wallets for user {}: {}".format(username, ", ".join(wallets))
        else:
            return "No wallets found for user {}".format(username)

    except Exception as e:
        print("Error retrieving wallets from database:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()


# Define a function to handle the "!show" command
def handle_show_command(command, username):
    tokens = command.split()
    if len(tokens) != 1:
        return "Invalid command: expected '!show'"
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["username"],
            password=db_config["password"]
        )
        cur = conn.cursor()

        # Retrieve the user's saved wallets from the database
        cur.execute(
            "SELECT wallet_address FROM wallets WHERE user_id = %s",
            (username,)
        )
        rows = cur.fetchall()
        if not rows:
            return "No wallets saved for user {}".format(username)
        wallets = "\n".join(row[0] for row in rows)
        return "Wallets saved for user {}:\n{}".format(username, wallets)

    except Exception as e:
        print("Error retrieving wallets from database:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    while True:
        command = input("Enter command: ")
        if command.startswith("!save"):
            handle_save_command(command, "test_user")
        elif command == "!show wallets":
            handle_show_wallets_command("test_user")
        elif command == "!show":
            handle_show_command(command, "test_user")
        elif command == "!exit":
            break
        else:
            print("Invalid command")
