"""
A very crude implementation of the TFGM/BeeNetwork "Metrolinks" OpenData API.

See get_next_station_departure below for details.
"""

import requests
import json
import re


class ReadToSubstringReader:
    """
    Wrapper around objects exposing a `read()` method which implements
    efficient read-up-to-substring style operations.
    """
    
    # Buffer of read data
    _buffer: bytearray
    
    # The start/end indices into the _buffer of valid data
    _start: int
    _end: int
    
    def __init__(self, reader, buffer_size: int = 2048) -> None:
        self._reader = reader
        
        self._buffer = bytearray(buffer_size)
        self._start = 0
        self._end = 0
    
    def _read_more(self) -> int:
        """
        Read more data into the buffer. Returns the number of bytes read. Does
        nothing if the buffer is full.
        """
        # Truncate the buffer
        if self._start > 0:
            length = self._end - self._start
            self._buffer[:length] = self._buffer[self._start:self._start + length]
            self._start = 0
            self._end = length
        
        # Append new data
        # XXX: Could use read-into but this breaks regular Python compatibility
        space = len(self._buffer) - self._end
        new_data = self._reader.read(space)
        self._buffer[self._end:self._end + len(new_data)] = new_data
        self._end += len(new_data)
        
        return len(new_data)
    
    def read_to_substring(self, substring: bytes) -> memoryview | None:
        """
        Attempt to read up to the next occurrence of the provided substring.
        Returns a memoryview of all unconsumed data upto and including that
        substring, if it is found. This becomes invalid on the next call to
        this function.  Returns None if the substring was not found before the
        buffer filled up or hit EOF.
        """
        while True:
            index = self._buffer.find(substring, self._start, self._end)
            if index >= 0:
                end = index + len(substring)
                view = memoryview(self._buffer)[self._start:end]
                self._start = end
                return view
            else:
                if self._read_more() == 0:
                    return None

    def read_next_json_object(self) -> "Any | None":
        """
        Skip forward to the next "{" and then attempt to read a valid JSON
        object, returning the deserialised object.
        
        The next '{' found in the stream must be the start of a valid JSON object.
        
        If no '{' is found, returns None.
        
        If no valid JSON object less than buffer_size bytes long can be
        decoded, an exception is thrown.
        """
        if not self.read_to_substring(b"{"):
            return None
        
        serialised = b"{"
        while len(serialised) <= len(self._buffer):
            body = self.read_to_substring(b"}")
            if not body:
                raise Exception("Couldn't find end of JSON object.")
            serialised += body
            try:
                return json.loads(serialised.decode("utf-8"))
                break
            except ValueError:
                # Incomplete JSON object, there must have been an '}' in a
                # nested object or string somewhere. Keep reading.
                pass
        
        raise Exception("JSON object too large.")


def parse_next_station_departure(
    json_stream,
    station: str,
    excluded_destinations: set[str] = set(),
) -> int | None:
    """
    Given a `read()`-able object returning a Metrolink API JSON response,
    return the number of minutes until the next departure from a named station.

    If excluded_destinations is given, excludes departures to any of the named
    stations.
    """
    # Since the Metrolink API response, and its decoded JSON structure, is too
    # large to fit in memory we must process it in a streaming fashion. We
    # could implement a streaming JSON parser, but since the API response has a very
    # simple structure, we just use a simple substring scanning approach
    # instead.
    #
    # The API response consists of a dictionary of the shape:
    #
    #     {
    #          "@odata.context":"https://opendataclientapi.azurewebsites.net/odata/$metadata#Metrolinks",
    #          "value":[...]
    #     }
    #
    # Where the 'value' field is an array of objects describing a platform's
    # departure board which we'd like to parse.
    
    cr = ReadToSubstringReader(json_stream)
    
    # Jump to the 'value' array (which is safe since the @odata.context field
    # has fixed content without any '[' or '{' characters.
    assert cr.read_to_substring(b"["), "No 'value' array found"

    waits = []
    while value := cr.read_next_json_object():
        # Determine the relevant departure times
        if value["StationLocation"] == station:
            for i in range(4):
                dest = value[f"Dest{i}"]
                wait = value[f"Wait{i}"]
                if dest and dest not in excluded_destinations:
                    waits.append(int(wait))

    if not waits:
        return None
    
    return min(waits)



def get_next_station_departure(
    api_key: str,
    station: str,
    excluded_destinations: set[str],
) -> int | None:
    """
    Get the number of minutes to the next departure from the specified station
    which is not destined for any station in excluded_destinations. Returns
    None if no departures are known.
    """
    resp = requests.get(
        "https://api.tfgm.com/odata/Metrolinks",
        headers={
            "User-Agent": "TramTimer",
            "Ocp-Apim-Subscription-Key": api_key,
        },
        stream=True,
    )
    if resp.status_code != 200:
        return None

    return parse_next_station_departure(
        json_stream=resp.raw,
        station=station,
        excluded_destinations=excluded_destinations,
    )

