import http.client

_UNKNOWN = 'UNKNOWN'
_MAXLINE = 65536


class MITMResponseClass(http.client.HTTPResponse):

    def _readall_chunked(self):
        assert self.chunked != _UNKNOWN
        value = []
        try:
            while True:
                chunk_left = self._get_chunk_left()
                if chunk_left is None:
                    break
                value.append(b'%X\r\n' % chunk_left)
                value.append(self._safe_read(chunk_left))
                value.append(b'\r\n')
                self.chunk_left = 0
            value.append(b'0\r\n\r\n')
            print(value)
            return b''.join(value)
        except http.client.IncompleteRead:
            raise http.client.IncompleteRead(b''.join(value))
