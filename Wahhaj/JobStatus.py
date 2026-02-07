import uuid

class JobStatus:
    """
    This class represents the status of a processing job in the system, It is used to track:
    - the job identifier
    - current progress
    - current state
    - optional status message
    """

    def __init__(self):
        #Create a unique ID for each job
        self.jobId = str(uuid.uuid4())

        #Percentage of completion (0 to 100)
        self.progress = 0

        #Message describing the current job state
        self.message = ""

        #Initial job state as defined in the class diagram
        #Possible values: Queued, Running, Done, Error
        self.state = "Queued"
