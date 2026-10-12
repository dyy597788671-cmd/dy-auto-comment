import ctypes
import os
import socket
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lan_bridge as bridge


class ReadConnection:
    def __init__(self, payload):
        self.payload = bytearray(payload)
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def sendall(self, value):
        self.requests.append(value)

    def recv(self, size):
        amount = min(size, 2, len(self.payload))
        value = bytes(self.payload[:amount])
        del self.payload[:amount]
        return value


class NativeCall:
    def __init__(self, operation):
        self.operation = operation

    def __call__(self, *args):
        return self.operation(*args)


class DeviceServiceTests(unittest.TestCase):
    def request(self, payload):
        connection = ReadConnection(payload)
        program_data = str(Path.cwd() / 'test-program-data')
        image = str(Path(program_data) / 'ShadowBot/support_x64/mobile/AndroidSDK/platform-tools/adb.exe')
        with patch.dict(os.environ, {'PROGRAMDATA': program_data}), \
             patch.object(bridge, '_adb_listener_pid', return_value=8396), \
             patch.object(bridge, '_process_image', return_value=image), \
             patch.object(bridge.socket, 'create_connection', return_value=connection) as connect, \
             patch.object(bridge.subprocess, 'run') as process:
            online = bridge._read_adb_online_devices()
            connect.assert_called_once_with(('127.0.0.1', 5037), timeout=2)
            process.assert_not_called()
        return online, connection

    def test_fragmented_host_response_reads_states_without_phone_commands(self):
        content = b'phone-a\tdevice\nphone-b\tdevice\nold\toffline\nlocked\tunauthorized\n'
        online, connection = self.request(b'OKAY' + ('%04x' % len(content)).encode('ascii') + content)
        self.assertEqual(online, {'phone-a', 'phone-b'})
        self.assertEqual(connection.requests, [b'000chost:devices'])

    def test_empty_live_list_is_zero_not_a_saved_flag_fallback(self):
        online, connection = self.request(b'OKAY0000')
        self.assertEqual(online, set())
        self.assertEqual(connection.requests, [b'000chost:devices'])

    def test_truncated_or_failed_service_response_is_an_error(self):
        for value in (b'FAIL0004test', b'OKAY0010x', b'OKAYxxxx'):
            with self.assertRaises((OSError, ValueError)):
                self.request(value)

    def test_other_adb_installation_is_not_counted_as_shadowbot(self):
        with patch.dict(os.environ, {'PROGRAMDATA': str(Path.cwd())}), \
             patch.object(bridge, '_adb_listener_pid', return_value=8396), \
             patch.object(bridge, '_process_image', return_value='other/platform-tools/adb.exe'), \
             patch.object(bridge.socket, 'create_connection') as connect:
            with self.assertRaises(OSError):
                bridge._read_adb_online_devices()
        connect.assert_not_called()

    def test_missing_listener_does_not_start_any_server(self):
        with patch.dict(os.environ, {'PROGRAMDATA': str(Path.cwd())}), \
             patch.object(bridge, '_adb_listener_pid', side_effect=OSError('无现有服务')), \
             patch.object(bridge.socket, 'create_connection') as connect, \
             patch.object(bridge.subprocess, 'run') as process:
            with self.assertRaises(OSError):
                bridge._read_adb_online_devices()
        connect.assert_not_called()
        process.assert_not_called()

    def test_native_listener_table_uses_port_5037_and_ignores_8200(self):
        address = struct.unpack('<I', socket.inet_aton('127.0.0.1'))[0]
        entries = [struct.pack('<6I', 2, address, socket.htons(port), 0, 0, owner)
                   for port, owner in ((8200, 8396), (5037, 8396), (8765, 9999))]
        table = struct.pack('<I', len(entries)) + b''.join(entries)

        def get_table(buffer, size, ordered, family, table_class, reserved):
            self.assertEqual((family, table_class, reserved), (2, 3, 0))
            ctypes.cast(size, ctypes.POINTER(ctypes.c_uint32))[0] = len(table)
            if buffer is None:
                return 122
            ctypes.memmove(buffer, table, len(table))
            return 0

        dll = SimpleNamespace(GetExtendedTcpTable=NativeCall(get_table))
        with patch.object(bridge.os, 'name', 'nt'), \
             patch.object(bridge.ctypes, 'WinDLL', create=True, return_value=dll):
            self.assertEqual(bridge._adb_listener_pid(), 8396)

    def test_native_process_query_opens_query_only_handle_and_closes_it(self):
        calls = []
        expected = 'C:\\ProgramData\\ShadowBot\\support_x64\\mobile\\AndroidSDK\\platform-tools\\adb.exe'

        def open_process(rights, inherit, pid):
            calls.append(('open', rights, inherit, pid))
            return 42

        def get_name(handle, flags, name, size):
            self.assertEqual((handle, flags), (42, 0))
            name.value = expected
            return 1

        dll = SimpleNamespace(OpenProcess=NativeCall(open_process),
                              QueryFullProcessImageNameW=NativeCall(get_name),
                              CloseHandle=NativeCall(lambda handle: calls.append(('close', handle)) or 1))
        with patch.object(bridge.ctypes, 'WinDLL', create=True, return_value=dll):
            self.assertEqual(bridge._process_image(8396), expected)
        self.assertEqual(calls, [('open', 0x1000, False, 8396), ('close', 42)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
