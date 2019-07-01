import os
import datetime
import asyncio
import requests
import functools
from   enum import Enum
from   http import HTTPStatus

ENDPOINTS_ENV            = "AZURE_CORELEDGER_SERVICES"
REQUESTS_TIMEOUT_ENV     = "AZURE_CORELEDGER_HTTP_TIMEOUT"
DEFAULT_REQUESTS_TIMEOUT = 1

StateValue = Enum("AzureAppState", "NA OK")

class Settings:
    def __init__(self, endpoints, timeout):
        self.endpoints = endpoints
        self.timeout = timeout

    @property
    def endpoints(self):
        return self._endpoints

    @endpoints.setter
    def endpoints(self, value):
        endpoints = value.split()
        assert isinstance(endpoints, list)
        assert endpoints
        self._endpoints = endpoints

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        if (value == None):
            self._timeout = DEFAULT_REQUESTS_TIMEOUT
        else:
            self._timeout = int(value)

        print("[{0}] You've set the next timeout value for the HTTP requests: {1}".format(datetime.datetime.now(), self._timeout))

class AzurePipelineHandler:
    _states = {}

    @classmethod
    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.handleHttpRequests())

    @classmethod
    def handleEnvVars(self):
        envData = os.getenv(ENDPOINTS_ENV)
        requestsTimeout = os.getenv(REQUESTS_TIMEOUT_ENV)
        settings = Settings(envData, requestsTimeout)
        return settings

    @classmethod
    def checkStatesReady(self):
        for index in self._states.values():
            if (index == StateValue.NA):
                return False

        return True

    @classmethod
    @asyncio.coroutine
    def handleHttpRequests(self):
        settings  = self.handleEnvVars()
        endpoints = settings.endpoints

        for index in range(len(endpoints)):
            self._states[endpoints[index]] = StateValue.NA

        loop = asyncio.get_event_loop()

        while not self.checkStatesReady():
            for index in range(len(endpoints)):
                value = endpoints[index]

                if not value:
                    raise Exception("The given endpoint from array is not a string.")

                print(value)
                future = loop.run_in_executor(None, functools.partial(requests.get, value, timeout=settings._timeout))
                response = yield from future
                print("[{0}] Response from: '{1}', HTTP response-code: {2}".format(datetime.datetime.now(), value, response.status_code))

                if (response.status_code == HTTPStatus.OK):
                    self._states[value] = StateValue.OK

handler = AzurePipelineHandler()
handler.run()
