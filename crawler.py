#!/usr/bin/env python
# General purpose crawler.

class Crawler:

    def __init__(self):
        self.jobs = []

    def add_job(self, job):
        self.jobs += job,

    def do_job(self, job):
        # override this function to do crawling
        print "job:", repr(job)

    def run(self):
        while len(self.jobs) > 0:
            job = self.jobs[0]
            self.jobs.remove(job)
            self.do_job(job)


if __name__ == "__main__":
    print "This shall be done!"
    dummy = Crawler()
    dummy.add_job(1)
    dummy.add_job(2)
    dummy.add_job('a')
    dummy.add_job(["hi", "there", 100])
    dummy.add_job({23:"dummy"})
    dummy.run()
