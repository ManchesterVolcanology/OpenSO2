# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 10:59:03 2019

@author: mqbpwbe2
"""

#========================================================================================
#================================== Get Station Status ==================================
#========================================================================================

def get_station_status(self, station):

    # Try to retrieve the station status
    time, status = self.stat_com[station].pull_status()

    self.station_widjets[station]['status_time'].set(time[:-7])
    self.station_widjets[station]['status'].set(status)
