import sys

from mock import (
    Mock, patch
)
from kiwi_obs_plugin.tasks.image_obs import ImageObsTask
from kiwi_obs_plugin.obs import obs_checkout_type


class TestImageObsTask:
    def setup(self):
        sys.argv = [
            sys.argv[0],
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
        self.task.command_args['--force'] = False
        self.task.command_args['--target-dir'] = '../data/target_dir'

    @patch('kiwi_obs_plugin.tasks.image_obs.Help')
    def test_process_image_obs_help(self, mock_kiwi_Help):
        Help = Mock()
        mock_kiwi_Help.return_value = Help
        self._init_command_args()
        self.task.command_args['help'] = True
        self.task.command_args['obs'] = True
        self.task.process()
        Help.show.assert_called_once_with(
            'kiwi::image::obs'
        )

    @patch('kiwi_obs_plugin.tasks.image_obs.OBS')
    @patch('shutil.copy')
    def test_process_image_obs_image(self, mock_shutil_copy, mock_OBS):
        obs = Mock()
        obs.fetch_obs_image.return_value = obs_checkout_type(
            checkout_dir='../data',
            profile='Kernel'
        )
        mock_OBS.return_value = obs
        self._init_command_args()
        self.task.command_args['--image'] = 'project/image'
        self.task.process()
        mock_OBS.assert_called_once_with(
            'project/image', False, 'obs_user'
        )
        obs.fetch_obs_image.assert_called_once_with(
            '../data/target_dir', False
        )
        obs.add_obs_repositories.assert_called_once_with(
            self.task.xml_state, 'Kernel', 'x86_64', 'images'
        )
        obs.print_repository_status.assert_called_once_with(
            obs.add_obs_repositories.return_value
        )
        obs.write_kiwi_config_from_state.assert_called_once_with(
            self.task.xml_state, '../data/appliance.kiwi'
        )
