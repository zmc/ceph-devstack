import pytest
import os
from datetime import datetime,timedelta
from ceph_devstack.cli import main
import random
import shutil
import string
import sys
import logging

'''
Using pytest paramtrization to test logs command with different 
combinations of runs, jobs, selection and if view file path flag is set.
Following parameter combination results in 5*2=10 test cases.
'''
@pytest.mark.parametrize("num_runs,num_jobs,selection",[(0,0,0),(2,0,0),(4,1,0),(4,3,2),(3, 2, 3)])
@pytest.mark.parametrize("flag_set",[ True, False])
def test_teuthology_logs(num_runs:int,num_jobs:int,selection:int, flag_set:bool,capsys:pytest.CaptureFixture,monkeypatch:pytest.MonkeyPatch,caplog:pytest.LogCaptureFixture) -> int:     
    """ This function tests the 'logs' command of ceph-devstack.
    
    Creates a directory structure with random logs and runs the 'logs' command.
    Checks if the logs are displayed correctly.
    Removes the directory structure after the test.

    Args:
    num_runs (int): Number of runs to be created.
    num_jobs (int): Number of jobs to be created.
    selection (int): The job id to be selected.
    flag_set (bool): Flag to set log file path.
    capsys (fixture): To capture stdout and stderr.
    monkeypatch (fixture): To patch the sys.argv for invoking cli with args and stdin for job selection.
    caplog (fixture): To capture logs.
    """
    logger = logging.getLogger(__name__)

    if flag_set:
        monkeypatch.setattr(sys, 'argv', [ sys.argv[0],'-c', 'ceph_devstack/resources/test/test_config.yaml', 'logs','--log-file'])
    else:
        monkeypatch.setattr(sys, 'argv', [ sys.argv[0],'-c', 'ceph_devstack/resources/test/test_config.yaml', 'logs'])
    monkeypatch.setattr('builtins.input', lambda name: str(selection))
    data_path = '/tmp/ceph-devstack'
    try:
        os.makedirs(data_path+'/archive', exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        return 1
    runs_dir={}
    if num_runs>0:
        for i in range(num_runs):
            end = datetime.now()
            start = end - timedelta(days=4)
            random_date = start + (end - start) * random.random()
            random_date=random_date.strftime('%Y-%m-%d_%H:%M:%S')
            try:
                os.makedirs(data_path+'/archive'+'/root-'+random_date+'-teuthology', exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating directory: {e}")
                return 1
            random_logs = []
            if num_jobs>0:
                for j in range(num_jobs):
                    try:
                        os.makedirs(data_path+'/archive'+'/root-'+random_date+'-teuthology/'+str(j), exist_ok=True)
                    except Exception as e:
                        logger.error(f"Error creating directory: {e}")
                        return 1
                    try:
                        with open(data_path+'/archive'+'/root-'+random_date+'-teuthology/'+str(j)+'/teuthology.log', 'w') as f:
                            random_logs.append(''.join(random.choices(string.ascii_letters, k=200)))
                            f.write(random_logs[-1])
                    except Exception as e:
                        logger.error(f"Error creating file: {e}")
                        return 1
            runs_dir[data_path+'/archive'+'/root-'+random_date+'-teuthology']=random_logs
    try:
        with pytest.raises(SystemExit) as main_exit:
            main()
    except Exception as e:
        logger.error(f"Error running main: {e}")
        return 1
    
    output, err = capsys.readouterr()
    try:
        shutil.rmtree(data_path+'/archive')
    except Exception as e:
        logger.error(f"Error removing directory: {e}")
        return 1
    
    runs_dir_list=list(runs_dir.keys())
    if num_runs>0:
        runs_dir_list.sort(key=lambda x: datetime.strptime(x.split('/')[-1].split('root-')[1].split('-teuthology')[0], '%Y-%m-%d_%H:%M:%S'))
    if num_runs < 1:
        assert main_exit.value.code == 1
        assert "No runs found!" in caplog.text
    elif num_jobs < 1:
        assert main_exit.value.code == 1
        assert "No jobs found!" in caplog.text
    elif selection not in range(num_jobs):
        assert main_exit.value.code == 1
        assert "Invalid job id!" in caplog.text
    elif flag_set:
        assert main_exit.value.code == 0
        assert  f"Log file path: {runs_dir_list[-1]}/{selection}/teuthology.log" in output
    else:
        assert main_exit.value.code == 0
        assert runs_dir[runs_dir_list[-1]][int(selection)] in output
