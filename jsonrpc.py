#!/usr/bin/env python
# -*- coding: utf-8

import json
import websocket

import config
import log

class ProtocolError(Exception):
    pass


class ServerProxy:

    def __init__(self, host, transport=None,
                 encoding=None, verbose=0,
                 allow_none=0):
        import urllib
        type, uri = urllib.parse.splittype(host)
        if type not in ('http',):
            raise IOError("unsupported RPC protocol")
        self.__host, self.__handler = urllib.parse.splithost(uri)
        if not self.__handler:
            self.__url = "ws://" + self.__host + '/ws/'
        if transport is None:
            transport = WSTransport()
        self.__transport = transport
        self.__encoding = encoding
        self.__verbose = verbose
        self.__allow_none = allow_none

    def __close(self):
        self.__transport.close()

    def __request(self, methodname, params):
        request = dumps(params, methodname)
        response = self._run_request(request, notify=True)
        return response['result']

    def _run_request(self, request, notify=None):
        log.add_request(request)
        response = self.__transport.request(self.__url, request)
        log.add_response(response)
        if not response:
            return None
        return_obj = loads(response)
        return return_obj

    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        return _Method(self.__request, name)

    def __call__(self, attr):
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport
        raise AttributeError("Attribute %r not found" % (attr,))

class JSONParser(object):
    def __init__(self, target):
        self.target = target

    def feed(self, data):
        self.target.feed(data)

    def close(self):
        pass

class JSONTarget(object):
    def __init__(self):
        self.data = []

    def feed(self, data):
        self.data.append(data)

    def close(self):
        return ''.join(self.data)

class WSTransport:

    def getparser(self):
        target = JSONTarget()
        return JSONParser(target), target

    def request(self, url, request_body):
        self.ws = websocket.create_connection(url)
        response = self.ws.handshake_response.status
        if response == 101:
            self.ws.send(request_body)
            result = self.response()
            return result

    def response(self):
        result = self.ws.recv()
        return result

class _Method:
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.__name)

    def __str__(self):
        return self.__repr__()

    def __dir__(self):
        return self.__dict__.keys()

class _Notify(object):
    def __init__(self, request):

        self._request = request

    def __getattr__(self, name):
        return _Method(self._request, name)

class MultiCallMethod(object):

    def __init__(self, method, notify=False):
        self.method = method
        self.params = []
        self.notify = notify

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0 and len(args) > 0:
            raise ProtocolError('JSON-RPC does not support both ' +
                                'positional and keyword arguments.')
        if len(kwargs) > 0:
            self.params = kwargs
        else:
            self.params = args

    def request(self, encoding=None, rpcid=None):
        return dumps(self.params, self.method, notify=self.notify)

    def __repr__(self):
        return '%s' % self.request()

    def __getattr__(self, method):
        new_method = '%s.%s' % (self.method, method)
        self.method = new_method
        return self

class MultiCallNotify(object):

    def __init__(self, multicall):
        self.multicall = multicall

    def __getattr__(self, name):
        new_job = MultiCallMethod(name, notify=True)
        self.multicall._job_list.append(new_job)
        return new_job

class MultiCallIterator(object):

    def __init__(self, results):
        self.results = results

    def __iter__(self):
        for i in range(0, len(self.results)):
            yield self[i]
        raise StopIteration

    def __getitem__(self, i):
        item = self.results[i]
        return item['result']

    def __len__(self):
        return len(self.results)

class MultiCall(object):

    def __init__(self, server):
        self._server = server
        self._job_list = []

    def _request(self):
        if len(self._job_list) < 1:
            return
        request_body = '[ {0} ]'.format(
            ','.join([job.request() for job in self._job_list]))
        responses = self._server._run_request(request_body)
        del self._job_list[:]
        if not responses:
            responses = []
        return MultiCallIterator(responses)

    @property
    def _notify(self):
        return MultiCallNotify(self)

    def __getattr__(self, name):
        new_job = MultiCallMethod(name)
        self._job_list.append(new_job)
        return new_job

    __call__ = _request

class _Method:
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __call__(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise ProtocolError(
                'Cannot use both positional and keyword arguments '
                '(according to JSON-RPC spec.)')
        if len(args) > 0:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.__name)

    def __str__(self):
        return self.__repr__()

    def __dir__(self):
        return self.__dict__.keys()


class Fault(object):
    def __init__(self, code=-32000, message='Server error', rpcid=None):
        self.faultCode = code
        self.faultString = message
        self.rpcid = rpcid

    def error(self):
        return {'code': self.faultCode, 'message': self.faultString}

    def response(self):
        return dumps(self, methodresponse=True)

    def __repr__(self):
        return '<Fault %s: %s>' % (self.faultCode, self.faultString)


class Payload(dict):
    def __init__(self):
        self.mtypes = (str)

    def request(self, method, params=[]):
        if type(method) is not str:
            raise ValueError('Method name must be a string.')
        request = {'method': method}
        if params:
            request['params'] = params
        return request

    def response(self, result=None):
        response = {'result': result}
        return response

    def error(self, code=-32000, message='Server error.'):
        error = self.response()
        error['result'] = None
        error['error'] = {'code': code, 'message': message}
        return error


def jdumps(obj, encoding='utf-8'):
    """encoding is necessary if we want to use Python version 2"""
    return json.dumps(obj)
    # return json.dumps(obj, encoding=encoding)


def jloads(json_string):
    return json.loads(json_string)


def dumps(params=[], methodname=None, methodresponse=None, notify=None):
    valid_params = (tuple, list, dict)
    if methodname in (str,) and \
            type(params) not in valid_params and \
            not isinstance(params, Fault):
        raise TypeError('Params must be a dict, list, tuple or Fault ' +
                        'instance.')
    _payload = Payload()
    if type(params) is Fault:
        response = _payload.error(params.faultCode, params.faultString)
        return jdumps(response)

    if type(methodname) not in (str, ) and methodresponse is not True:
        raise ValueError('Method name must be a string or'
                         ' methodresponse must be set to True.')

    if config.use_jsonclass is True:
        import jsonclass
    params = jsonclass.dump(params)

    if methodresponse is True:
        response = _payload.response(params)
        return jdumps(response)
    request = None
    if notify is True:
        request = _payload.notify(methodname, params)
    else:
        request = _payload.request(methodname, params)
    return jdumps(request)


def loads(data):
    if data == '':
        return None
    result = jloads(data)
    return result


def isbatch(result):
    if type(result) not in (list, tuple):
        return False
    if len(result) < 1:
        return False
    if not isinstance(result[0], dict):
        return False
    return True

Server = ServerProxy
