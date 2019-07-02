import os
import asyncio
import requests
import functools
import time
import datetime as dtp
from   enum import Enum
from   http import HTTPStatus

ENDPOINTS_ENV            = "AZURE_CORELEDGER_SERVICES"
REQUESTS_TIMEOUT_ENV     = "AZURE_CORELEDGER_HTTP_TIMEOUT"
MAX_WAIT_MINUTES_ENV     = "AZURE_CORELEDGER_MAX_WAIT_MINUTES"
DEFAULT_RATIO            = 60
DEFAULT_REQUESTS_TIMEOUT = 1
DEFAULT_MAX_WAIT_MINUTES = 15

StateValue = Enum("AzureAppState", "NA OK")

class Settings:
    def __init__(self, endpoints, timeout, pipelineTimeout):
        self.endpoints       = endpoints
        self.timeout         = timeout
        self.pipelineTimeout = pipelineTimeout

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

        print("[{0}] You've set the next timeout value for the HTTP requests: {1}".format(dtp.datetime.now(), self._timeout))

    @property
    def pipelineTimeout(self):
        return self._pipelineTimeout

    @pipelineTimeout.setter
    def pipelineTimeout(self, value):
        if (value == None):
            self._pipelineTimeout = DEFAULT_MAX_WAIT_MINUTES
        else:
            self._pipelineTimeout = int(value)

        print("[{0}] You've set the next timeout value for the Azure pipeline work: {1}".format(dtp.datetime.now(), self._pipelineTimeout))

class AzurePipelineHandler:
    _states = {}
    _startedDatetime = None

    @classmethod
    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.handleHttpRequests())

    @classmethod
    def handleEnvVars(self):
        envData         = os.getenv(ENDPOINTS_ENV)
        requestsTimeout = os.getenv(REQUESTS_TIMEOUT_ENV)
        pipelineTimeout = os.getenv(MAX_WAIT_MINUTES_ENV)
        settings = Settings(envData, requestsTimeout, pipelineTimeout)
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

        self._startedDatetime = dtp.datetime.now()
        print("Started check at: {0}\nCurrent limit: {1} minutes".format(self._startedDatetime, settings.pipelineTimeout))
        loop = asyncio.get_event_loop()

        while not self.checkStatesReady():
            for index in range(len(endpoints)):
                value = endpoints[index]

                if not value:
                    raise Exception("The given endpoint from array is not a string.")

                print(value)

                try:
                    if (self.checkTerminateState(settings.pipelineTimeout)):
                        raise Exception("Can't wait any longer... Check your Azure Apps, maybe it was manually terminated/stopped.")

                    future = loop.run_in_executor(None, functools.partial(requests.get, value, timeout=settings._timeout))
                    response = yield from future
                    print("[{0}] Response from: '{1}', HTTP response-code: {2}".format(dtp.datetime.now(), value, response.status_code))

                    if (response.status_code == HTTPStatus.OK):
                        self._states[value] = StateValue.OK

                except (requests.exceptions.RequestException, ValueError) as exception:
                    print(exception)

    @classmethod
    def checkTerminateState(self, limit):
        firstTuple  = time.mktime(self._startedDatetime.timetuple())
        secondTuple = time.mktime(dtp.datetime.now().timetuple())
        minutes = int(secondTuple - firstTuple) / DEFAULT_RATIO
        print("Current diff-limit: {0}".format(minutes))
        return minutes > limit

handler = AzurePipelineHandler()
handler.run()
