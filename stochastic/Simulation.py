# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 23:56:18 2024

@author: saeed
"""

import numpy as np


class simulation():
    
    def __init__(self):
        
        #print("simulation created")
        self.service_level=[]
    
        
    def total_delay(self,instance,scenario,overtime,L):
        
        nb_scenario=len(scenario.travel_time)
        
        total_lateness=np.zeros(nb_scenario,dtype=int)  #total delay for all routes of the instance 
        total_overtime=np.zeros(nb_scenario,dtype=int)   #total overtime for all routes of the instance 
        
        run_lateness=np.zeros(nb_scenario,dtype=int)   #if there is any lateness for patients in a run 
        run_overtime=np.zeros(nb_scenario,dtype=int)  #if there is overtime for any of aides in a run 
        
        for i in range(len(instance.list_route)):
            
            route=instance.list_route[i][0]
            visit_time=instance.list_schedule[i]
            
            total_delay,overal_state,aide_overtime,aide_state=self.route_delay(scenario,route,visit_time,instance,overtime,L)
            
            total_delay*=instance.list_route[i][1]  #calculate delay over a week 
            aide_overtime*=instance.list_route[i][1]
            
            total_lateness+=total_delay
            total_overtime+=aide_overtime
            
            for s in range(nb_scenario):
                if run_lateness[s]==0 and overal_state[s]==1:
                    run_lateness[s]=1
                if run_overtime[s]==0 and aide_state[s]==1:
                    run_overtime[s]=1 
        
        
        average_total_lateness=total_lateness.sum()/nb_scenario
        average_total_overtime=total_overtime.sum()/nb_scenario
        
        average_run_lateness=run_lateness.sum()/nb_scenario
        average_run_overtime=run_overtime.sum()/nb_scenario
        
        max_total_lateness=total_lateness.max()
        
        
        service_record={}
        for i,k in self.service_level:
            if i not in service_record:
                service_record[i]=[k]
            else:
                service_record[i].append(k)
                
        for i in service_record.keys():
            service_record[i]=min(service_record[i])
        
        service_record=sorted(service_record.items())
        
        value=[]
        
        for i in service_record:
            value.append(i[1])
        
        mean_service=sum(value)/len(value)
        min_service=min(value)
        
        return average_total_lateness,average_total_overtime,average_run_lateness,average_run_overtime,max_total_lateness,service_record,mean_service,min_service
    
            
            
        
        
    def route_delay(self,scenario,route,visit_time,instance,overtime,L):
        
        num_node=len(route)-1
        num_scenario=len(scenario.travel_time)
        arrival=np.empty((num_scenario,num_node),dtype=float)  #to keep mean of arrival time for each node
        start=np.empty((num_scenario,num_node),dtype=float)  #to keep mean of start time for each node
        
        state=np.zeros((num_scenario,num_node),dtype=int)   # whether each patient is visited with delay for each scenario or not 
        overal_state=np.zeros(num_scenario,dtype=int)    #if we have any delay for each patient for each scenario it gets 1
        
        total_delay=np.zeros(num_scenario,dtype=int)  #the sum of delay for patients in each scenario 
        
        aide_overtime=np.zeros(num_scenario,dtype=int)  # the amount of overtime for aide in each scenario 
        aide_state=np.zeros(num_scenario,dtype=int)   #whether the aide works overtime in each scenario or not 
    
    
        
        for i in range(1,num_node+1):
            #print("node is {}".format(i))
        
            if i==1:
            
                #print(" the node : {}".format(i))
            
                from_i=route[i-1]
                to_j=route[i]


                for s in range(num_scenario):
                
                    #print("scenario {} for node {}".format(s,i))
                
                    arrival[s][i-1]=visit_time[i-1]+int(np.round(scenario.travel_time[s][from_i*instance.number_node+to_j]))
                    start[s][i-1]=max(visit_time[i],arrival[s][i-1])
                
                    #print("arrival: {}".format(arrival[s][i-1]))
                
                    #print("start: {}".format(start[s][i-1]))
                
                    if start[s][i-1]>visit_time[i]+L:
                        state[s][i-1]=1
                        total_delay[s]+=start[s][i-1]-visit_time[i]-L
                        overal_state[s]=1
                        
                    #print("state is {}".format(state[s][i-1]))
        
            elif i==num_node:
            
                #print(" the node : {}".format(i))
                from_i=route[i-1]
                to_j= route[i]
                
                
                for s in range(num_scenario):
                
                    #print("scenario {} for node {}".format(s,i))
                
                    arrival[s][i-1]=start[s][i-2]+int(np.round(scenario.service_time[s][from_i]))
                
                    #print("arrival: {}".format(arrival[s][i-1]))
                
                    if arrival[s][i-1]>visit_time[i]+overtime:
                    
                        state[s][i-1]=1
                        aide_overtime[s]=arrival[s][i-1]-visit_time[i]-overtime
                        aide_state[s]=1
                
                    #print("state is {}".format(state[s][i-1]))
                    
                    
            
            else:
                #print(" the node : {}".format(i))
                
                from_i=route[i-1]
                to_j= route[i]
                                
                for s in range(num_scenario):
                
                    #print("scenario {} for node {}".format(s,i))
                
                    arrival[s][i-1]=start[s][i-2]+int(np.round(scenario.service_time[s][from_i]))+int(np.round(scenario.travel_time[s][from_i*instance.number_node+to_j]))
                    start[s][i-1]=max(visit_time[i],arrival[s][i-1])
                
                    #print("arrival: {}".format(arrival[s][i-1]))
                    #print("start: {}".format(start[s][i-1]))
                
                    if start[s][i-1]>visit_time[i]+L :
                    
                        state[s][i-1]=1
                        total_delay[s]+=start[s][i-1]-visit_time[i]-L
                        overal_state[s]=1
                   
                
         #print("state is {}".format(state[s][i-1]))        
                
        service_level=[(route[i]-instance.number_aide,1-state[:,i-1].sum()/num_scenario) for i in range(1,num_node)]
        for i in range(len(service_level)):
            self.service_level.append(service_level[i])
    
   

        return total_delay,overal_state,aide_overtime,aide_state     #np.sum(state,axis=0)/num_scenario,state
                
                    
           
                    

    
    
    

