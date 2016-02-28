import http.client

_UNKNOWN = 'UNKNOWN'
_MAXLINE = 65536


class MITMResponseClass(http.client.HTTPResponse):

    # def _readall_chunked(self):
    #     assert self.chunked != _UNKNOWN
    #     value = []
    #     try:
    #         while True:
    #             chunk_left = self._get_chunk_left()
    #             if chunk_left is None:
    #                 value.append(b'\r\n0\r\n\r\n')
    #                 break
    #             value.append()
    #             value.append(self._safe_read(chunk_left))
    #             self.chunk_left = 0
    #         print(value)
    #         return b''.join(value)
    #     except http.client.IncompleteRead:
    #         raise http.client.IncompleteRead(b''.join(value))
    #
    # def _get_chunk_left(self):
    #     # return self.chunk_left, reading a new chunk if necessary.
    #     # chunk_left == 0: at the end of the current chunk, need to close it
    #     # chunk_left == None: No current chunk, should read next.
    #     # This function returns non-zero or None if the last chunk has
    #     # been read.
    #     chunk_left = self.chunk_left
    #     if not chunk_left: # Can be 0 or None
    #         if chunk_left is not None:
    #             # We are at the end of chunk. dicard chunk end
    #             self._safe_read(2)  # toss the CRLF at the end of the chunk
    #         try:
    #             chunk_left = self._read_next_chunk_size()
    #         except ValueError:
    #             raise http.client.IncompleteRead(b'')
    #         if chunk_left == 0:
    #             # last chunk: 1*("0") [ chunk-extension ] CRLF
    #             self._read_trailer()
    #             # we read everything; close the "file"
    #             self._close_conn()
    #             chunk_left = None
    #         self.chunk_left = chunk_left
    #     return chunk_left
    #
    # def _read_trailer(self):
    #     trailer = []
    #     while True:
    #         line = self.fp.readline(_MAXLINE + 1)
    #         if len(line) > _MAXLINE:
    #             raise http.client.LineTooLong("trailer line")
    #         if not line:
    #             # a vanishingly small number of sites EOF without
    #             # sending the trailer
    #             break
    #         if line in (b'\r\n', b'\n', b''):
    #             trailer.append(line)
    #             break
    #
    #     return b''.join(trailer)
