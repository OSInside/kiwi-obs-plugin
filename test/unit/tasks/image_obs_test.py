import sys

from mock import (
    Mock, patch
)
from kiwi_obs_plugin.tasks.image_obs import ImageObsTask


class TestImageObsTask:
    def setup(self):
        sys.argv = [
            sys.argv[0],
            '--profile', 'foo',
            'image', 'obs',
            '--image', 'openSUSE:Leap:15.2:Images/livecd-openSUSE',
            '--user', 'obs_user',
            '--target-dir', '../data/target_dir'
        ]
        self.task = ImageObsTask()

    def _init_command_args(self):
        self.task.command_args = {}
        self.task.command_args['help'] = False
        self.task.command_args['obs'] = False
        self.task.command_args['--user'] = 'obs_user'
        self.task.command_args['--arch'] = None
        self.task.command_args['--repo'] = False
        self.task.command_args['--ssl-no-verify'] = None
        self.task.command_args['--target-dir'] = '../data/target_dir'

    @patch('kiwi_obs_plugin.tasks.image_obs.Help')
    def test_process_system_boxbuild_help(self, mock_kiwi_Help):
        Help = Mock()
        mock_kiwi_Help.return_value = Help
        self._init_command_args()
        self.task.command_args['help'] = True
        self.task.command_args['obs'] = True
        self.task.process()
        Help.show.assert_called_once_with(
            'kiwi::image::obs'
        )
