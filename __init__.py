from config import Config
config = Config.instance()
from log import History
logs = History.instance()
from jsonrpc import Server, MultiCall, Fault
from jsonrpc import ProtocolError, loads, dumps