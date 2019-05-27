from jsonprclibveles.config import Config
config = Config.instance()
from jsonprclibveles.history import History
logs = History.instance()
from jsonprclibveles.jsonrpc import Server, MultiCall, Fault
from jsonprclibveles.jsonrpc import ProtocolError, loads, dumps
