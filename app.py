import logging
import argparse
import re
import sys
import subprocess
import datetime
import json
from enum import Enum
from colorama import Fore, Style, init

# Create the parser
parser = argparse.ArgumentParser(description="Run checks")

# Add the arguments
parser.add_argument('--expiration', action='store_true',
                    help='Check for expirations')
parser.add_argument('--unrelayed', action='store_true',
                    help='Check for unrelayed packets')
parser.add_argument('--balance', action='store_true',
                    help='Check for low balance')
parser.add_argument('--all', action='store_true',
                    help='Check all')
# This will automatically reset the color back to default after each print
init(autoreset=True)

# Define a custom ANSI escape sequence for orange color
ORANGE = "\033[38;5;208m"  # ANSI escape sequence for orange color
RESET = Style.RESET_ALL

# Define the LogLevel enum


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

# Define a custom logger


class ColoredLogger(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        message = self.format(record)
        level = record.levelname
        if record.levelno == logging.DEBUG:
            level = f"{Fore.YELLOW}{level}{RESET}"
        elif record.levelno == logging.INFO:
            level = f"{Fore.GREEN}{level}{RESET}"
        elif record.levelno == logging.WARNING:
            level = f"{ORANGE}{level}{RESET}"
        elif record.levelno in [logging.ERROR, logging.CRITICAL]:
            level = f"{Fore.RED}{level}{RESET}"
        print(f"{level}: {message}")


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(ColoredLogger())

# Configure the paths, namespaces, and relayers separately
CONFIG = {
    "native": {
        "tokens": {
            "loki": {
                "alerts": {
                    "low_balance_warn_threshold": 214000000,
                    "low_balance_error_threshold": 42,
                }
            },
            "factory/kujira1qk00h5atutpsv900x202pxx42npjr9thg58dnqpa72f2p7m2luase444a7/uusk": {
                "alerts": {
                    "low_balance_warn_threshold": 5000000,
                    "low_balance_error_threshold": 1000000,
                }
            }
        }
    },
    "paths": {
        "kujira": {
            "mainnet-kujira-akash": {
                "chain_name": "akash",
                "channel": "channel-64",
                "tokens": {
                    "uakt": {
                        "alerts": {
                            "low_balance_warn_threshold": 14000000,
                            "low_balance_error_threshold": 3000000,
                        }
                    }
                }
            },
            "mainnet-kujira-mantle": {
                "chain_name": "assetmantle",
                "channel": "channel-65",
                "tokens": {
                    "umntl": {
                        "alerts": {
                            "low_balance_warn_threshold": 1092000000,
                            "low_balance_error_threshold": 218000000,
                        }
                    }
                }
            },
            "mainnet-kujira-crescent": {
                "chain_name": "crescent",
                "channel": "channel-67",
                "tokens": {
                    "ucre": {
                        "alerts": {
                            "low_balance_warn_threshold": 146000000,
                            "low_balance_error_threshold": 29000000,
                        }
                    }
                }
            },
            "mainnet-kujira-neutron": {
                "chain_name": "neutron",
                "channel": "channel-75",
                "tokens": {
                    "transfer/channel-1/uatom": {
                        "alerts": {
                            "low_balance_warn_threshold": 475000,
                            "low_balance_error_threshold": 95100,
                        }
                    }
                }
            },
            "mainnet-kujira-omniflixhub": {
                "chain_name": "omniflixhub",
                "channel": "channel-70",
                "tokens": {
                    "uflix": {
                        "alerts": {
                            "low_balance_warn_threshold": 13000000,
                            "low_balance_error_threshold": 2660000,
                        }
                    }
                }
            },
            "mainnet-kujira-regen": {
                "chain_name": "regen",
                "channel": "channel-68",
                "tokens": {
                    "uregen": {
                        "alerts": {
                            "low_balance_warn_threshold": 56000000,
                            "low_balance_error_threshold": 11000000,
                        }
                    }
                }
            }
        },
        "odin": {
            "mainnet-odin-osmosis": {
                "chain_name": "osmosis",
                "channel": "channel-3",
                "tokens": {
                    "uosmo": {
                        "alerts": {
                            "low_balance_warn_threshold": 8000000,
                            "low_balance_error_threshold": 1650000,
                        }
                    }
                }
            },
            "mainnet-odin-axelar": {
                "chain_name": "axelar",
                "channel": "channel-37",
                "tokens": {
                    "uaxl": {
                        "alerts": {
                            "low_balance_warn_threshold": 10000000,
                            "low_balance_error_threshold": 2000000,
                        }
                    }
                }
            }
        }
    },
    "namespaces": {
        "kujira": "customer-kujira",
        "odin": "customer-odin"
    },
    "relayers": {
        "kujira": "relayer--mainnet",
        "odin": "relayer--mainnet"
    },
    "expiration_days_threshold_warning": 5,
    "expiration_days_threshold_error": 2,
    "log_level": LogLevel.INFO
}

logging.basicConfig(format='%(levelname)s: %(message)s',
                    level=CONFIG['log_level'].value)


def run_subprocess_command(command: list) -> str:
    """
    Run a subprocess command and return the output as a string.

    Args:
        command (list): The command to be executed as a list of strings.

    Returns:
        str: The output of the subprocess command as a string.
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        logging.error(f"Error while running subprocess command: {e}")
        return ""


def check_expiration(path: dict):
    """
    Check the expiration of clients on a given path.

    Args:
        namespace (str): The namespace in which the relayer is deployed.
        relayer (str): The name of the relayer.
        path (str): The path to check the expiration of clients.
    """
    logging.debug(f"Checking for expirations on: {path}")
    command = ['kubectl', 'exec', '-q', '-n', namespace,
               f'deploy/{relayer}', '--', 'rly', 'q', 'clients-expiration', path]
    output = run_subprocess_command(command)
    if output:
        expiring_clients = parse_expiring_clients(output)
        warn_expiring_clients(expiring_clients)


def check_expirations(category):
    category_paths = CONFIG["paths"].get(category)
    if category_paths is None:
        logging.error(f"Category '{category}' not found in the configuration.")
        return

    namespace = CONFIG["namespaces"].get(category)
    if namespace is None:
        logging.error(f"Namespace not found for category '{category}'.")
        return

    relayer = CONFIG["relayers"].get(category)
    if relayer is None:
        logging.error(f"Relayer not found for category '{category}'.")
        return

    desired_keys = [key for key in category_paths.keys()]
    for key in desired_keys:
        if key not in category_paths:
            logging.error(f"Path '{key}' not found in the configuration.")
            continue
        check_expiration(key)
    logging.debug("Expiration check completed.")


def check_unrelayed_packets(namespace: str, relayer: str, path: str, path_data: dict):
    """
    Check for unrelayed packets on a given path.

    Args:
        namespace (str): The namespace in which the relayer is deployed.
        relayer (str): The name of the relayer.
        path (dict): The path to check for unrelayed packets.
    """
    logging.debug(
        f"Checking for unrelayed-packets on chain_name: {path_data['chain_name']}")
    command = ['kubectl', 'exec', '-q', '-n', namespace,
               f'deploy/{relayer}', '--', 'rly', 'q', 'unrelayed-packets', path, path_data['channel']]
    output = run_subprocess_command(command)
    if output:
        if is_unrelayed_packets_populated(output):
            warn_unrelayed_packets()
        else:
            logging.info(
                f"No unrelayed packets found on chain_name: {path_data['chain_name']}")


def check_low_path_balance(namespace: str, relayer: str, path: dict):
    """
    Check if the balance of a chain_name is below the low balance threshold.

    Args:
        namespace (str): The namespace in which the relayer is deployed.
        relayer (str): The name of the relayer.
        path (dict): The path to check the balance.
    """
    logging.debug(
        f"Checking for low balance on chain_name: {path['chain_name']}")
    command = ['kubectl', 'exec', '-q', '-n', namespace,
               f'deploy/{relayer}', '--', 'rly', 'q', 'balance', path['chain_name']]
    output = run_subprocess_command(command)

    if output:
        balance_data = parse_balance(output)
        # Extract the balance value
        for balance in balance_data['balances']:

            amount = balance['amount']
            denom = balance['denom']
            if denom in path["tokens"]:
                # Convert balance to integer
                # Check if balance is below the error threshold
                if amount and int(amount) <= path["tokens"][denom]["alerts"]["low_balance_error_threshold"]:
                    logging.error(
                        f"Low balance detected on chain_name: {path['chain_name']}. Balance: {amount} {denom}")

                # Check if balance is below the warning threshold
                elif amount and int(amount) <= path["tokens"][denom]["alerts"]["low_balance_warn_threshold"]:
                    logging.warning(
                        f"Low balance detected on chain_name: {path['chain_name']}. Balance: {amount} {denom}")
                else:
                    logging.info(
                        f"balance ok on chain_name: {path['chain_name']}. Balance: {amount} {denom}")


def check_low_native_balance(namespace: str, relayer: str, chain_name: str):
    """
    Check if the balance of a chain_name is below the low balance threshold.

    Args:
        namespace (str): The namespace in which the relayer is deployed.
        relayer (str): The name of the relayer.
        path (dict): The path to check the balance.
    """
    logging.debug(
        f"Checking for low balance on chain_name: {chain_name}")
    command = ['kubectl', 'exec', '-q', '-n', namespace,
               f'deploy/{relayer}', '--', 'rly', 'q', 'balance', chain_name]
    output = run_subprocess_command(command)

    if output:
        balance_data = parse_balance(output)
        # Extract the balance value
        for balance in balance_data['balances']:
            amount = balance['amount']
            denom = balance['denom']
            # print(amount, denom)
            if denom in CONFIG["native"]["tokens"]:
                # Convert balance to integer
                # Check if balance is below the error threshold
                if amount and int(amount) <= CONFIG["native"]["tokens"][denom]["alerts"]["low_balance_error_threshold"]:
                    logging.error(
                        f"Low balance detected on chain_name: {chain_name}. Balance: {amount} {denom}")

                # Check if balance is below the warning threshold
                elif amount and int(amount) <= CONFIG["native"]["tokens"][denom]["alerts"]["low_balance_warn_threshold"]:
                    logging.warning(
                        f"Low balance detected on chain_name: {chain_name}. Balance: {amount} {denom}")
                else:
                    logging.info(
                        f"balance ok on chain_name: {chain_name}. Balance: {amount} {denom}")


def warn_unrelayed_packets():
    """Print a warning message for unrelayed packets."""
    logging.warning("There are unrelayed packets!")


def parse_expiring_clients(output: str) -> list:
    """
    Parse the output of the 'rly q clients-expiration' command and extract expiring clients.

    Args:
        output (str): The output of the 'rly q clients-expiration' command.

    Returns:
        list: A list of expiring clients.
    """
    return [line for line in output.split('\n') if line.startswith('client')]


def warn_expiring_clients(expiring_clients: list):
    """
    Print warning or error messages for expiring clients.

    Args:
        expiring_clients (list): A list of expiring clients.
    """
    now = datetime.datetime.now()
    for client in expiring_clients:
        client_id, chain_id = extract_expiration_info(client)
        expiration_date = extract_expiration_date(client)
        if expiration_date:
            remaining_time = expiration_date - now
            days = remaining_time.days
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            expiration_message = f"Client {client_id} on {chain_id} will expire in {days} days {hours} hours {minutes} minutes {seconds} seconds"
            if expiration_date <= now + datetime.timedelta(days=CONFIG["expiration_days_threshold_error"]):
                logging.error(expiration_message)
            elif expiration_date < now + datetime.timedelta(days=CONFIG["expiration_days_threshold_warning"]):
                logging.warning(expiration_message)
            else:
                logging.info(expiration_message)


def extract_expiration_info(client: str) -> tuple:
    """
    Extract client ID and chain ID from the client expiration string.

    Args:
        client (str): The client expiration string.

    Returns:
        tuple: A tuple containing client ID and chain ID.
    """
    parts = client.split()
    client_id = parts[1] if len(parts) > 1 else None
    chain_id = parts[2].strip("()") if len(parts) > 2 else None
    return client_id, chain_id


def extract_expiration_date(client: str) -> datetime.datetime:
    """
    Extract the expiration date from the client expiration string.

    Args:
        client (str): The client expiration string.

    Returns:
        datetime.datetime: The expiration date.
    """
    parts = client.split()
    if len(parts) >= 7:
        expiration_date_str = ' '.join(parts[-5:-2])
        try:
            expiration_date = datetime.datetime.strptime(
                expiration_date_str, "(%d %b %y")
        except ValueError:
            expiration_date_str = ' '.join(parts[-4:-1])
            expiration_date = datetime.datetime.strptime(
                expiration_date_str, "%d %b %Y")
        return expiration_date
    return None


def is_unrelayed_packets_populated(output: str) -> bool:
    """
    Check if the output of 'rly q unrelayed-packets' command indicates unrelayed packets.

    Args:
        output (str): The output of the 'rly q unrelayed-packets' command.

    Returns:
        bool: True if unrelayed packets are found, False otherwise.
    """
    data = json.loads(output)
    return data["src"] is not None or data["dst"] is not None


def parse_balance(output: str):
    """
    Parse the output of the 'rly q balance' command and extract the account and balances.

    Args:
        output (str): The output of the 'rly q balance' command.

    Returns:
        dict: An object with the account and a list of balances.
    """
    balances = []
    parts = output.split()
    account = parts[1].strip("{}")
    for part in parts[3:]:
        tokens = part.strip("{}").split(",")
        for token in tokens:
            match = re.match(r'(\d+)(.*)', token)
            if match:
                amount, denom = match.groups()
                amount = int(amount)  # convert string to integer
                balances.append({"amount": amount, "denom": denom})
    return {"account": account, "balances": balances}


def get_chain_names() -> list:
    """
    Get a list of all chain_names.

    Returns:
        list: A list of chain_names.
    """
    command = ['rly', 'paths', 'list']
    output = run_subprocess_command(command)
    if output:
        chain_names = []
        lines = output.split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 2:
                chain_name = parts[1].strip().split()[0]
                if chain_name not in chain_names and chain_name != 'odin':
                    chain_names.append(chain_name)
        return chain_names
    return []


def setup_config():
    """
    Setup the initial configuration by adding chain_names and tokens to the CONFIG dictionary.
    """
    chain_names = get_chain_names()
    for category, category_paths in CONFIG["paths"].items():
        for path in category_paths.values():
            chain_name = path['chain_name']
            if chain_name in chain_names:
                command = ['rly', 'q', 'balance', chain_name]
                output = run_subprocess_command(command)
                if output:
                    tokens = parse_tokens(output)
                    if tokens:
                        path['tokens'] = tokens


def parse_tokens(output: str) -> list:
    """
    Parse the output of the 'rly q balance' command and extract the tokens.

    Args:
        output (str): The output of the 'rly q balance' command.

    Returns:
        list: A list of tokens.
    """
    tokens = []
    parts = output.split()
    for part in parts:
        if part.startswith("10000transfer"):
            tokens.append(part)
    return tokens


# Setup the initial configuration
setup_config()

# Parse the arguments
args = parser.parse_args()

for category, category_paths in CONFIG["paths"].items():
    namespace = CONFIG["namespaces"][category]
    relayer = CONFIG["relayers"][category]

    if args.expiration:
        logging.debug(f"Checking for expirations on {category} paths:")
        check_expirations(category)

    if args.unrelayed:
        logging.debug(f"Checking for unrelayed-packets on {category} paths:")
        for path in category_paths:
            check_unrelayed_packets(
                namespace, relayer, path, category_paths[path])

    if args.balance:
        logging.debug(f"Checking for low balance on {category} paths:")
        check_low_native_balance(namespace, relayer, category)
        for path in category_paths.values():
            check_low_path_balance(namespace, relayer, path)

    if args.all:
        logging.debug(f"Checking for expirations on {category} paths:")
        check_expirations(category)

        logging.debug(f"Checking for unrelayed-packets on {category} paths:")
        for path in category_paths:
            check_unrelayed_packets(
                namespace, relayer, path, category_paths[path])

        logging.debug(f"Checking for low balance on {category} paths:")
        check_low_native_balance(namespace, relayer, category)
        for path in category_paths.values():
            check_low_path_balance(namespace, relayer, path)

    if not args.expiration and not args.unrelayed and not args.balance and not args.all:
        parser.print_help()
        sys.exit(1)
