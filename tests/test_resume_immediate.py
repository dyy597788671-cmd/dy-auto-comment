import json
import unittest
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import core_runner as core
import lan_bridge as web
import module1 as bridge
from test_device_entry import complete, read, setup
from test_execution_output import temporary_root


class ImmediateResumeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = self.stack.enter_context(temporary_root())
        self.root = Path(folder)
        self.stack.enter_context(patch.object(bridge, 'PROJECT_ROOT', folder))
        self.infos = setup(self.root, 4)
        config = self.root / 'config/settings.json'
        settings = json.loads(config.read_text(encoding='utf-8'))
        settings.update(cooldown_min_seconds=600, cooldown_max_seconds=600)
        config.write_text(json.dumps(settings), encoding='utf-8')
        bridge.start_execution(self.infos)
        self.bindings = bridge.prepare_devices(self.infos)

    def state(self):
        return json.loads((self.root / 'data/runtime_state.json').read_text(encoding='utf-8'))

    def fail(self, index, partial=False):
        binding = self.bindings[index]
        task = read(binding)
        gateway = core.UnifiedGateway(str(self.root), binding['sender_account_id'])
        if partial:
            plan = gateway.generate_strategy(seed=17, task_id=task['task_id'], run_token=task['run_token'])
            saved = [dict(action=plan['execution_order'][0], status='PASSED', message='confirmed')]
            gateway.save_action_results(task['task_id'], task['run_token'], saved)
        result = bridge.finish_device_error(binding['sender_account_id'], binding['device_id'],
                                            'Synthetic element not found', task['task_id'])
        self.assertTrue(result['released'])
        return task

    def resume(self, account=None):
        return web.resume(self.root, '1005', 'test-owner', True, account)

    def test_four_devices_two_success_two_fail_resume_without_restart(self):
        for binding in self.bindings[:2]:
            complete(self.root, read(binding))
        self.fail(2, partial=True)
        self.fail(3)
        before = self.state()
        original = deepcopy(before['project_accounts']['1005'])
        failures = {b['sender_account_id'] for b in self.bindings[2:]}
        self.assertEqual(set(before['dispatch']['skipped_accounts']), failures)
        self.assertEqual(bridge.prepare_devices(self.infos), [])

        self.resume()
        state = self.state()
        for account in failures:
            self.assertEqual(state['devices'][account]['state'], 'READY')
            self.assertIsNone(state['devices'][account]['cooldown_until'])
        self.assertEqual(state['dispatch']['skipped_accounts'], [])
        self.assertEqual(state['project_accounts']['1005']['assignment'], original['assignment'])
        for binding in self.bindings[:2]:
            account = binding['sender_account_id']
            self.assertEqual(state['project_accounts']['1005']['accounts'][account], original['accounts'][account])
            self.assertEqual(state['devices'][account], before['devices'][account])

        with patch('time.sleep', side_effect=AssertionError('resume must not sleep for cooldown')):
            ready = bridge.prepare_devices(self.infos)
            self.assertEqual({b['sender_account_id'] for b in ready}, failures)
            for binding in ready:
                account = binding['sender_account_id']
                task = read(binding)
                prior = original['accounts'][account]
                self.assertEqual(task['comment_content'], prior['comment_content'])
                self.assertEqual(task['physical_device_id'], prior['physical_device_id'])
                self.assertEqual(task['assignment_id'], original['assignment']['assignment_id'])
                self.assertEqual(task.get('action_results', []), prior['result']['executed_actions'])
                if prior.get('plan'):
                    gateway = core.UnifiedGateway(str(self.root), account)
                    remaining = gateway.remaining_strategy(task['task_id'], task['run_token'])
                    self.assertEqual(remaining['execution_order'], prior['plan']['execution_order'][1:])

    def test_single_device_resume_does_not_release_other_failed_device(self):
        self.fail(0)
        self.fail(1)
        before = self.state()
        selected = self.bindings[0]['sender_account_id']
        other = self.bindings[1]['sender_account_id']
        self.resume(selected)
        state = self.state()
        self.assertEqual(state['devices'][selected]['state'], 'READY')
        self.assertNotIn(selected, state['dispatch']['skipped_accounts'])
        self.assertEqual(state['devices'][other], before['devices'][other])
        self.assertIn(other, state['dispatch']['skipped_accounts'])
        self.assertEqual(state['project_accounts']['1005']['accounts'][other],
                         before['project_accounts']['1005']['accounts'][other])

    def test_already_pending_resume_interrupts_existing_wait_within_five_seconds(self):
        self.fail(0)
        for binding in self.bindings[1:]:
            complete(self.root, read(binding))
        account = self.bindings[0]['sender_account_id']
        self.resume(account)
        gateway = core.UnifiedGateway(str(self.root), account)
        # An existing waiting caller must notice the next web resume promptly.
        with gateway._session(recover=False) as state:
            state['devices'][account].update(state='COOLDOWN',
                cooldown_until=(core._utcnow() + timedelta(seconds=600)).isoformat())
            gateway._save_state(state)
        sleeps = []
        def resume_during_wait(seconds):
            sleeps.append(seconds)
            self.assertLessEqual(seconds, 5.0)
            self.resume(account)
        with patch('time.sleep', side_effect=resume_during_wait):
            ready = bridge.prepare_devices(self.infos)
        self.assertEqual(len(sleeps), 1)
        self.assertEqual([b['sender_account_id'] for b in ready], [account])

    def test_pending_legacy_resume_clears_leftover_skip_and_cooldown(self):
        self.fail(0)
        account = self.bindings[0]['sender_account_id']
        self.resume(account)
        gateway = core.UnifiedGateway(str(self.root), account)
        with gateway._session(recover=False) as state:
            state['devices'][account].update(state='COOLDOWN',
                cooldown_until=(core._utcnow() + timedelta(seconds=600)).isoformat())
            state['dispatch']['skipped_accounts'].append(account)
            gateway._save_state(state)
        self.resume(account)
        self.resume(account)
        state = self.state()
        self.assertEqual(state['devices'][account]['state'], 'READY')
        self.assertNotIn(account, state['dispatch']['skipped_accounts'])

    def test_resume_does_not_release_blocked_device(self):
        binding = self.bindings[0]
        task = read(binding)
        gateway = core.UnifiedGateway(str(self.root), binding['sender_account_id'])
        gateway.record_result(task['task_id'], 'FAILED', [],
            error_code='SECURITY_CHALLENGE_DETECTED', run_token=task['run_token'])
        with self.assertRaises(core.EngineError) as raised:
            self.resume(binding['sender_account_id'])
        self.assertEqual(raised.exception.code, 'DEVICE_UNAVAILABLE')
        self.assertEqual(self.state()['devices'][binding['sender_account_id']]['state'], 'BLOCKED')

    def test_resume_keeps_live_ownership_of_another_task(self):
        for index in range(4):
            self.fail(index)
        path = self.root / 'data/task_cases.xlsx'
        book = core.load_workbook(path)
        book.active.append(['1006', 'another task', 'author', 0, 'PENDING', None, None,
                            '12345', '视频', 'a\nb\nc\nd\ne', 4])
        book.save(path)
        book.close()
        future = core._utcnow() + timedelta(seconds=601)
        with patch.object(core, '_utcnow', return_value=future):
            bridge.start_execution(self.infos)
            next_bindings = bridge.prepare_devices(self.infos)
            task = read(next_bindings[0])
            self.assertEqual(task['task_id'], '1006')
            account = next_bindings[0]['sender_account_id']
            before = self.state()['devices'][account]
            self.resume(account)
            self.assertEqual(self.state()['devices'][account], before)
            self.assertEqual(before['state'], 'BUSY')


if __name__ == '__main__':
    unittest.main()
