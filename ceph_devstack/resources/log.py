import os
from datetime import datetime
from ceph_devstack import logger

class LogCapabilities:
    def __init__(self, path=None,job_id=None):
        self.job_id = job_id or None
        self.path = path or "~/.local/share/ceph-devstack/archive"

    def find_logs_location(self,):
        user_path = os.path.expanduser(self.path)
        if os.path.exists(user_path):
            dirs = [d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))]
            
            if dirs:
                dirs.sort(key=self._extract_timestamp, reverse=True)
                latest_dir = dirs[0]
                teuthology_logfiles = []
                for root, dirs, files in os.walk(os.path.join(user_path, latest_dir)):
                    if 'teuthology.log' in files:
                        if self.job_id is not None:
                            if os.path.basename(root) == str(self.job_id):
                                    teuthology_logfilePath = os.path.join(root, 'teuthology.log')
                                    teuthology_logfiles.append(teuthology_logfilePath)
                            else:
                                continue
                        else:
                            teuthology_logfilePath = os.path.join(root, 'teuthology.log')
                            teuthology_logfiles.append(teuthology_logfilePath)
                return teuthology_logfiles
            return []  
        else:
            return [] 
        
    def getPath(self):
        teuthology_logfile = self.find_logs_location()
        if teuthology_logfile:
            for idx, log in enumerate(teuthology_logfile):
                logger.info(f"{idx + 1}: {log}")
        else:
            logger.info("teuthology.log not found in default dir. Try with --log-dir")

    def print_logs(self):
        teuthology_logfile = self.find_logs_location()
        if teuthology_logfile:
            for idx, log in enumerate(teuthology_logfile):
                logger.info(f"{idx + 1}: {log}")

            if len(teuthology_logfile) > 1:
                selected_index = int(input("Multiple teuthology.log files found. Please select the log file by number: ")) - 1
                if 0 <= selected_index < len(teuthology_logfile):
                    selected_log = teuthology_logfile[selected_index]
                else:
                    logger.info("Invalid selection.")
                    return []
            else:
                selected_log = teuthology_logfile[0]

            with open(selected_log, 'r') as file:
                log_contents = file.read()
                logger.info(log_contents)
        else:
            logger.info("teuthology.log not found.")
                
                

    def _extract_timestamp(self, directory_name):
        try:
            timestamp_str = directory_name.split('-')[1] + '-' + directory_name.split('-')[2] + '-' + directory_name.split('-')[3] + '_' + directory_name.split('-')[4]
            timestamp_str = timestamp_str.split('_')[0] + '_' + timestamp_str.split('_')[1].split('-')[0]
            return datetime.strptime(timestamp_str, '%Y-%m-%d_%H:%M:%S')
        except Exception as e:
            return datetime.min  

   