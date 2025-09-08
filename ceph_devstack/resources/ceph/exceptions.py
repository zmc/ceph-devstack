class TooManyJobsFound(Exception):
    def __init__(self, jobs: list[str]):
        self.jobs = jobs
