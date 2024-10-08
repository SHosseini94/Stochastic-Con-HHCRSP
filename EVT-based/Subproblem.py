# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 22:25:37 2024

@author: saeed
"""

"""
This class solves the subproblem, scheduling and routing of patients.
Each subproblem associates with one aide weekly scheduling. 
Thus, it requires to have access to instance, aide_id, and list of patients
assigned to it (which is taken from master problem). 
These are the inputs entered when we create the subproblem object.   

# The jobs this class does are:
# 
# 1. Generate Cut: 
#     It checks the being feasibility of subproblem, which means the 
    subproblem should be feasible for all days individually and 
    also it should satisfy the time consistency and weekly worktime 
    constraints. If it is not the case, we should create the 
    benders cut to add to the master problem, removes this current 
    assignment solution. To check the feasibility of subproblem,
    we can, first, check the feasibility of daily subproblem; 
    so we define a function, check_if_day_feasible 


       a. check if day feasible: create a CP model and add the
       constraints that is, no_overlap between tasks of day, fix
       first and last tasks. check the solve status. If it was infeasible,
       then we would create a cut, otherwise we return the true as output.
       The cut is a kind of strong cut. 


# Asumptions:
# 
#   1. scenarios for each route not for each day/route 
        (it means there isn't any difference for total time for same
         route in different days of a week), since the time window for
        both patients and aides don't change with days.
# 
#   2. Only one fail results in scenario fail. 
# 
# 

    I try to copy the deterministic version to the subproblem, 
    then I will try to add approximation constraints using BlackBox


# It works properly :)
"""


from docplex.cp.model import *
from docplex.cp.expression import *
from docplex.cp.solution import *

import numpy as np
from scipy.stats import poisson
from scipy.stats import norm




class Subproblem():
    
    
    def __init__(self,instance,aide_id,list_Pik_per_day,l,overtime,alpha,TCov,
                 SCov):
        
        
        self.instance=instance
        self.aide_id=aide_id
        self.list_Pik_per_day=list_Pik_per_day
        self.alpha=alpha   #service level 
        self.overtime=overtime
        self.TCov=TCov
        self.SCov=SCov
        
        
        # to keep all the unique assignments during a week 
        self.assignment_pattern=[]   
        
        self.travel_time=[self.instance.distance_matrix[i][j]  for i in range
                          (self.instance.number_node)
                          for j in range(self.instance.number_node)]
        
        self.service_time=[i.visit_duration for i in self.instance.list_patient]
        
        for d in range(self.instance.horizon):
            if self.list_Pik_per_day[d] not in self.assignment_pattern and self.list_Pik_per_day[d]:
                self.assignment_pattern.append(self.list_Pik_per_day[d])
                
        
        self.number_pattern=len(self.assignment_pattern)
        
        self.number_repeated_pattern=[0 for d in range(self.number_pattern)]
        for d in range(self.instance.horizon):
            for i in range(self.number_pattern):
                if self.list_Pik_per_day[d]==self.assignment_pattern[i]:
                    self.number_repeated_pattern[i]+=1
                    
        
        self.nb_points=[len(self.assignment_pattern[d])+2 for d in range(self.number_pattern)]
        self.tasks_per_day=[[] for i in range(self.number_pattern)]
        self.work_time=[None for i in range(self.number_pattern)]
        self.sequence=[None for i in range(self.number_pattern)]
        
        self.list_pairs=[]
        
        self.L=l  #allowable delay 
        
    
        
        self.visit_time=[[] for i in range(self.number_pattern)]
        self.route=[[] for i in range(self.number_pattern)]
        
        self.start=[[] for i in range(self.number_pattern)]
        

        
        
               
    def generate_cut(self,list_feasible_day_per_aide,list_cuts,final_call):
        
        
        l=[set(self.list_Pik_per_day[d]) for d in range(self.instance.horizon)]
        self.union_patients=list(set().union(*l))
            
       
        self.time_window={i:integer_var(min=self.instance.list_patient[i].time_window[0],
                                        max=self.instance.list_patient[i].time_window[1]-self.instance.list_patient[i].visit_duration
                                        ,name="time_window_patient_{}".format(i))
                          for i in self.union_patients}
        
        
        
        #fixed start and end for care giver 
        self.time_window_start=self.instance.list_aide[self.aide_id].time_window_start[0]
        self.time_window_end=self.instance.list_aide[self.aide_id].time_window_end[1]
        
        # Create a CpoModel 
        self.sub=CpoModel(name="Cp model of aide_{}".format(self.aide_id+1))
        
        self.itv_to_pnt={} 
        self.pnt_id={}
        
            
        for d in range(self.number_pattern):
            
            
            #changed 
            
            self.itv_to_pnt[d]={}
            self.pnt_id[d]={}
            
            
            tasks=[]
            visit_time=[]
            for i in range(self.nb_points[d]):
                
                if i!=0 and i!=self.nb_points[d]-1:
                    location=self.instance.list_patient[self.assignment_pattern[d][i-1]].location
                    tasks.append(interval_var(name="task_pnt_{}_{}".format(location,d)))
                    visit_time.append(integer_var(min=self.time_window_start,max=self.time_window_end,name="visit_node_{}_pattern_{}".format(i,d)))
                    
                    
                    
                elif i==0:
                    tasks.append(interval_var(name="task_start_depot_{}".format(d)))
                    visit_time.append(integer_var(min=self.time_window_start,max=self.time_window_end,name="visit_start_depot_{}".format(d)))
                    self.sub.add(visit_time[i]==start_of(tasks[i]))
                else:
                    tasks.append(interval_var(name="task_end_depot_{}".format(d)))
                    visit_time.append(integer_var(min=self.time_window_start,max=self.time_window_end,name="visit_end_depot_{}".format(d)))
                    self.sub.add(visit_time[i]==start_of(tasks[i]))
                
                
                #self.sub.add(visit_time[i]==start_of(tasks[i]))
            
            for i in range(1,self.nb_points[d]-1):
                
                self.sub.add(any([visit_time[i]==self.time_window[self.assignment_pattern[d][j-1]] for j in range(1,self.nb_points[d]-1)]))
                
                self.sub.add(visit_time[i-1]<visit_time[i])
            
            self.sub.add(all_diff(visit_time))
                
            
                            
                                      
                                      
                    
                
            #tasks=interval_var_list(self.nb_points[d],name="tasks_{}_{}".format(self.aide_id,d+1))  # tasks related to this pattern
            self.tasks_per_day[d]=tasks
            work=interval_var(name="work_time_{}_{}".format(self.aide_id+1,d+1))   # total work time of this pattern
            self.work_time[d]=work
            
            # specify the interval variables' attributes, such as size and start:
                
            self.set_tasks_values(d)
            
            seq=sequence_var(self.tasks_per_day[d],types=[i for i in range(self.nb_points[d])],name="sequence_{}_{}".format(self.aide_id+1,d+1))
            self.sequence[d]=seq
            
            distance_matrix=self.compute_transition_matrix(d)
            
            self.sub.add(no_overlap(seq,distance_matrix,1))
            self.sub.add(first(seq,self.tasks_per_day[d][0]))
            self.sub.add(last(seq,self.tasks_per_day[d][self.nb_points[d]-1]))
            self.sub.add(span(work,[self.tasks_per_day[d][j] for j in range(1,self.nb_points[d]-1)]))
            
            
          
            #arrival_statistics=CpoBlackboxFunction(impl=self.arrival_approximation,dimension=2)
            arrival_statistics=CpoBlackboxFunction(impl=self.arrival_approximation,dimension=2*(self.nb_points[d]-1))
            
            for i in range(self.nb_points[d]):
                if i==0:
                    self.itv_to_pnt[d][self.tasks_per_day[d][i]]=self.instance.list_aide[self.aide_id].location_start
                    self.pnt_id[d][self.instance.list_aide[self.aide_id].location_start]=i
                elif i==self.nb_points[d]-1:
                    self.itv_to_pnt[d][self.tasks_per_day[d][i]]=self.instance.list_aide[self.aide_id].location_end
                    self.pnt_id[d][self.instance.list_aide[self.aide_id].location_end]=i
                else:
                    self.itv_to_pnt[d][self.tasks_per_day[d][i]]=self.instance.list_patient[self.assignment_pattern[d][i-1]].location
                    self.pnt_id[d][self.instance.list_patient[self.assignment_pattern[d][i-1]].location]=i
                
               
            
            
            stats=arrival_statistics(seq,tasks,d)
            index=0
            
            for v in range(1,self.nb_points[d]):
                
                
                if v!=self.nb_points[d]-1:
                    self.sub.add(stats[index]+self.alpha*stats[index+1]<= visit_time[v]+self.L)
                    
                    self.sub.add(start_of(tasks[v])==self.time_window[self.assignment_pattern[d][v-1]])
                    
                else:  #only allow to work maximum for overtime longer than their end time window on each day 
                    self.sub.add(stats[index]+self.alpha*stats[index+1]<= visit_time[v]+self.overtime)
                    
                index+=2
              
          
             
        #"""
        self.union_patients.sort()
        value=""
        for id in self.union_patients:
            value+=str(id)+"-"
        
        value=""
        for d in range(self.number_pattern):
            for b in self.assignment_pattern[d]:     #added 22/11/05
                value+=str(b)+"-"
            value+="/"
        

        
        
        
        self.sub.add(sum([length_of(self.work_time[d])*self.number_repeated_pattern[d] for d in range(self.number_pattern)])
               <=self.instance.list_aide[self.aide_id].maximum_work_time)
        
        
        
        #file=open('CPOModel_approx.txt','a')
        #self.sub.export_model(file)
        
        sol=self.sub.solve(LogVerbosity="Quiet",Workers=1)  #Workers=4 TimeLimit=10 LogVerbosity="Quiet"
        
        
        if (sol):
            #print("yes")
                          
            solve_time=sol.get_solve_time()
            solve_complete_sub=1
            status=True
            time_limit=False
            self.instance.list_feasible_per_aide[self.aide_id].append(value) 
            
            #print("solving time is {}".format(solve_time))
            
            if final_call==True:
                
                
                for i in self.union_patients:
                    self.instance.list_patient[i].visit_time=sol.get_var_solution(self.time_window[i]).value
                    
                #new
                for d in range(self.number_pattern):
                    self.instance.list_aide[self.aide_id].route.append([])
                    self.instance.list_aide[self.aide_id].schedule.append([])
                    
                    seq=sol.get_var_solution(self.sequence[d])
                    value=seq.get_value()
                    for i in range(len(value)-1):
                        if i==0:
                            from_location=self.instance.list_aide[self.aide_id].location_start
                            from_time=self.instance.list_aide[self.aide_id].time_window_start[0]
                            
                            to_name=value[i+1].get_name()
                            m,n,location,b=to_name.split('_',3)
                            to_location=int(location)
                            to_time=self.instance.list_patient[to_location-self.instance.number_aide].visit_time
                            
                            self.instance.list_aide[self.aide_id].schedule[d].append(from_time)
                            self.instance.list_aide[self.aide_id].route[d].append(from_location)
                            
                            self.instance.list_aide[self.aide_id].route[d].append(to_location)
                            self.instance.list_aide[self.aide_id].schedule[d].append(to_time)
                            
                        elif i==len(value)-2:
                            from_name=value[i].get_name()
                            m,n,location,b=from_name.split('_',3)
                            from_location=int(location)
                            to_location=self.instance.list_aide[self.aide_id].location_end
                            to_time=self.instance.list_aide[self.aide_id].time_window_end[1]
                            
                            #self.instance.list_aide[self.aide_id].route[d].append(from_location)
                            self.instance.list_aide[self.aide_id].route[d].append(to_location)
                            self.instance.list_aide[self.aide_id].schedule[d].append(to_time)
                            
                        else:
                            from_name=value[i].get_name()
                            m,n,location,b=from_name.split('_',3)
                            from_location=int(location)
            
                            
                            to_name=value[i+1].get_name()
                            m,n,location,b=to_name.split('_',3)
                            to_location=int(location)
                            to_time=self.instance.list_patient[to_location-self.instance.number_aide].visit_time
                            
                            self.instance.list_aide[self.aide_id].route[d].append(to_location)
                            self.instance.list_aide[self.aide_id].schedule[d].append(to_time)
                    
                    self.instance.list_route.append((self.instance.list_aide[self.aide_id].route[d],self.number_repeated_pattern[d]))
                    self.instance.list_schedule.append(self.instance.list_aide[self.aide_id].schedule[d])
                            
                                
                    
                    
  
                  
            #sol.write(file) 
            cut=(self.aide_id,self.list_pairs)
            list_cuts.append(cut)
            
            return time_limit,status,solve_complete_sub,list_cuts
        else:
            
            #sol.write(file)
            solve_time=sol.get_solve_time()
            solve_complete_sub=1
            status=False
            time_limit=False
            
            #print("solving time is {}".format(solve_time))
            if solve_time>=10:
                time_limit=True
                #print("time limit is happen")
            
            for d in range(self.instance.horizon):
                if self.list_Pik_per_day[d]:
                    for i in self.list_Pik_per_day[d]:
                        if self.instance.list_patient[i].availability==2:# or self.instance.list_patient[i].availability==1 :
                            self.list_pairs.append((i,d))   #(patient_id,day)
            if not self.list_pairs:
                print("there is not any free patient to add to the cut")
            else:
                list_patient_per_aide_for_cut=(self.aide_id,self.list_pairs)
                list_cuts.append(list_patient_per_aide_for_cut)  # add to the cut should be added to the master problem
                return time_limit,status,solve_complete_sub,list_cuts
              
                    
            
        #file.close()
                    
                                
    def set_tasks_values(self,d):
        
        for i in range(self.nb_points[d]):
            if i==0:    #start base 
                self.tasks_per_day[d][i].set_start_min(self.instance.list_aide[self.aide_id].time_window_start[0])
                self.tasks_per_day[d][i].set_start_max(self.instance.list_aide[self.aide_id].time_window_start[0])
                self.tasks_per_day[d][i].set_size(0)
            elif i==self.nb_points[d]-1:  #end base 
                self.tasks_per_day[d][i].set_start_min(self.instance.list_aide[self.aide_id].time_window_end[1])
                self.tasks_per_day[d][i].set_start_max(self.instance.list_aide[self.aide_id].time_window_end[1])
                self.tasks_per_day[d][i].set_size(0)
            else:   #patient 
                
                index=self.assignment_pattern[d][i-1]  #patient id self.assignment_pattern[d]
                self.tasks_per_day[d][i].set_start_min(self.instance.list_patient[index].time_window[0])
                self.tasks_per_day[d][i].set_start_max(self.instance.list_patient[index].time_window[1]-self.instance.list_patient[index].visit_duration)
                self.tasks_per_day[d][i].set_size(self.instance.list_patient[index].visit_duration)
                
    
    
    def get_route_values(self,d):
        
        for i in range(self.nb_points[d]):

            if i==0:
                self.sub.add(self.visit_time[d][i]==self.time_window_start) 
                self.sub.add(self.route[d][i]==self.instance.list_aide[self.aide_id].location_start)
            elif i==self.nb_points[d]-1:
                self.sub.add(self.visit_time[d][i]==self.time_window_end)  
                self.sub.add(self.route[d][i]==self.instance.list_aide[self.aide_id].location_end)
            else:
                #self.sub.add(any([self.visit_time[d][i]==start_of(self.tasks_per_day[d][j]) for j in
                 #                 (1,self.nb_points[d]-1)]))
                
                self.sub.add(any([self.visit_time[d][i]==self.time_window[j] for j in self.assignment_pattern[d]]))
                #"""
                node=0
                #task=[self.tasks_per_day[d][j] for j in range(1,self.nb_points[d]-1)]
                task=[self.time_window[j] for j in self.assignment_pattern[d]]
                
                for j in task:
                    self.sub.add(if_then(self.visit_time[d][i]==j,self.route[d][i]==
                                     self.assignment_pattern[d][node]+self.instance.number_aide))
                    
                    self.sub.add(if_then(self.route[d][i]==
                                     self.assignment_pattern[d][node]+self.instance.number_aide,self.visit_time[d][i]==j))
                    node+=1
                #""" 
                
    def check_subroute_success(self,d,v):
        
        # d: day v:position in a route 
        
        if v==1:
            total_time=element(self.travel_time,self.route[d][v-1]*self.instance.number_node+self.route[d][v])
        else:
            service_time=element(self.service_time,self.route[d][v-1]-self.instance.number_aide)
            travel_time=element(self.travel_time,self.route[d][v-1]*self.instance.number_node+self.route[d][v])
            total_time=service_time+travel_time
        
        
        
        
        if v==self.nb_points[d]-1:
            
            finish=integer_var(name="finish_work_pattern{}".format(d+1))
            self.sub.add(finish==self.start[d][v-1]+service_time)
            self.sub.add(finish<=self.visit_time[d][v]+self.overtime)
            
        else:
            
            arrival=integer_var(name="arrival_pattern{}_node{}".format(d+1,v+1)) 
            start=integer_var(name="start_pattern{}_node{}".format(d+1,v+1)) 
            
            self.sub.add(arrival==self.start[d][v-1]+total_time)
            self.sub.add(if_then(arrival<self.visit_time[d][v],(start==self.visit_time[d][v])))
        
            self.sub.add(if_then((self.visit_time[d][v]<=arrival),(start==arrival)))
        
            self.sub.add(arrival<=self.visit_time[d][v]+self.L)
        
            self.start[d].append(start)
        
    def compute_transition_matrix(self,k):
        
        transition_matrix=np.zeros((self.nb_points[k],self.nb_points[k]),dtype=int)
        for i in range(self.nb_points[k]):
            if i==0:
                location_from=self.instance.list_aide[self.aide_id].location_start
            elif i==self.nb_points[k]-1:
                location_from=self.instance.list_aide[self.aide_id].location_end
            else:
                location_from=self.instance.list_patient[self.assignment_pattern[k][i-1]].location
            for j in range(self.nb_points[k]):
                if j==0:
                    location_to=self.instance.list_aide[self.aide_id].location_start
                elif j==self.nb_points[k]-1:
                    location_to=self.instance.list_aide[self.aide_id].location_end
                else:
                    location_to=self.instance.list_patient[self.assignment_pattern[k][j-1]].location
                        
                transition_matrix[i][j]=self.instance.distance_matrix[location_from][location_to]
                
        
        return transition_matrix
    """
    def approximate_start_time_stats(self,mu1,mu2,theta,sigma1,sigma2):
        
        mean=mu1*norm.cdf((mu1-mu2)/theta)+mu2*norm.cdf((mu2-mu1)/theta)+theta*norm.pdf((mu1-mu2)/theta)
        
        variance=(mu1**2+sigma1**2)*norm.cdf((mu1-mu2)/theta)+(mu2**2+sigma2**2)*norm.cdf((mu2-mu1)/theta)+(mu1+mu2)*theta*norm.pdf((mu1-mu2)/theta)-mean**2
        std=np.sqrt(variance)
        
        return mean, std
    """
    
    #for only one pattern 
    
    def approximate_start_time_stats(self,mu1,mu2,theta,sigma1,sigma2):
        
        mean=mu1*norm.cdf((mu1-mu2)/theta)+mu2*norm.cdf((mu2-mu1)/theta)+theta*norm.pdf((mu1-mu2)/theta)
        
        variance=(mu1**2+sigma1**2)*norm.cdf((mu1-mu2)/theta)+(mu2**2+sigma2**2)*norm.cdf((mu2-mu1)/theta)+(mu1+mu2)*theta*norm.pdf((mu1-mu2)/theta)-mean**2
        
        
        if variance<0:
            variance=0
        
        #std=np.sqrt(variance)
        std=variance
        
        
        return mean, std
    
    
    #for only one pattern 
    
    def arrival_approximation(self,sequence,tasks,d):  #all_visit_time
        
        route=[]
        visit_time=[]
        for i,itv in enumerate(sequence):
            order=self.itv_to_pnt[d][itv]
            route.append(order)
            index=self.pnt_id[d][order]
            visit_time.append(tasks[index].start)
        
        #index_task=self.pnt_id[d][route[position]]
        #print(index_task)
        
        num_node=len(route)-1
        
        mean_arrival=np.empty(num_node,dtype=np.float64)  #to keep mean of arrival time for each node
        std_arrival=np.empty(num_node,dtype=np.float64)   # to keep standard deviation of arrival time for each node 
        
        mean_start=np.empty(num_node,dtype=np.float64)  #to keep mean of start time for each node
        std_start=np.empty(num_node,dtype=np.float64)   # to keep standard deviation of start time for each node 
        
        all_stat=[]
        #print(route)
        #print(visit_time)
        
        
        for i in range(1,num_node+1):
            
            if i == 1:
                
                
                from_i=route[i-1]
                to_j=route[i]
                
                mean_arrival[i-1]=visit_time[i-1]+self.instance.distance_matrix[from_i][to_j]
                
                std_arrival[i-1]=self.instance.distance_matrix[from_i][to_j]*self.TCov
                
                mu1=mean_arrival[i-1]
                mu2=visit_time[i]
                
                sigma1=std_arrival[i-1]
                sigma2=0
                
                theta=sigma1+0.000001
                
                #print("mean_arrival of {} is {}".format(to_j,mean_arrival[i-1]))
                #print("st_arrival of {} is {}".format(to_j,std_arrival[i-1]))
                
            
                mean_start[i-1],std_start[i-1]=self.approximate_start_time_stats(mu1,mu2,theta,sigma1,sigma2)
                
                #print("mean_start of {} is {}".format(to_j,mean_start[i-1]))
                #print("std_start of {} is {}".format(to_j,std_start[i-1]))
                
                
            
            elif i==num_node:
                
                from_i=route[i-1]
                to_j= route[i]
                
                #service time at node i 
                
                visit_duration_mean_i=self.instance.list_patient[from_i-self.instance.number_aide].visit_duration
                visit_duration_std_i=self.SCov*visit_duration_mean_i
                
                # finish work time 
                mean_arrival[i-1]=mean_start[i-2]+visit_duration_mean_i
                
                variance=std_start[i-2]+visit_duration_std_i**2
                
                std_arrival[i-1]=np.sqrt(variance)
                
                #print("mean_arrival of {} is {}".format(to_j,mean_arrival[i-1]))
                #print("st_arrival of {} is {}".format(to_j,std_arrival[i-1]))
                
                
                
            else:
                
                from_i=route[i-1]
                to_j= route[i]
                
                #service time at node i 
                
                visit_duration_mean_i=self.instance.list_patient[from_i-self.instance.number_aide].visit_duration
                visit_duration_std_i=self.SCov*visit_duration_mean_i
                
                mean_arrival[i-1]=mean_start[i-2]+visit_duration_mean_i+self.instance.distance_matrix[from_i][to_j]
                
                variance=std_start[i-2]+visit_duration_std_i**2+(self.instance.distance_matrix[from_i][to_j]*self.TCov)**2
                std_arrival[i-1]=np.sqrt(variance)
                
                #print("mean_arrival of {} is {}".format(to_j,mean_arrival[i-1]))
                #print("st_arrival of {} is {}".format(to_j,std_arrival[i-1]))
                mu1=mean_arrival[i-1]
                mu2=visit_time[i]
                
                
                sigma1=std_arrival[i-1]
                sigma2=0
                theta=sigma1+0.000001
                
                mean_start[i-1],std_start[i-1]=self.approximate_start_time_stats(mu1,mu2,theta,sigma1,sigma2)
                
                #print("mean_start of {} is {}".format(to_j,mean_start[i-1]))
                #print("std_start of {} is {}".format(to_j,std_start[i-1]))
            
            #all_stat.append(int(self.pnt_id[d][route[i]]))
            all_stat.append(mean_arrival[i-1])
            all_stat.append(std_arrival[i-1])
            
                
                
                
                #mean_arrival, std_arrival
        #print(mean_arrival)
        
        #print(std_arrival)
        
    
        #print("arrival mean for position {} is {} and arrival standard deviation is {}".format(position,mean_arrival[position-1],std_arrival[position-1]))
        return all_stat
                
    
    
    
    def arrival_approximation_2(self,sequence,d,patient): #visit_time
        
        
        route=[]
        visit_time=[]
        
        for i,itv in enumerate(sequence):
            order=self.itv_to_pnt[d][itv]
            route.append(order)
            visit_time.append(itv.get_start())
        
        print(route)
        print(visit_time)
        
        index_patient=route.index(patient+self.instance.number_aide)
        print(index_patient)
        
        
        
        if index_patient!=1:
            
            prev=[route[i] for i in range(1,index_patient+1)] 
            num_node=len(prev)
            
            print(prev)
            
            mean_arrival=np.empty(num_node,dtype=np.float64)
            std_arrival=np.empty(num_node,dtype=np.float64)
            
            mean_start=np.empty(num_node,dtype=np.float64)
            std_start=np.empty(num_node,dtype=np.float64)
            
            for i in range(index_patient):
                
                from_i=route[i]
                to_j=route[i+1]
                
                if i==0:
                    mean_arrival[i]=visit_time[i]+self.instance.distance_matrix[from_i][to_j]
                    std_arrival[i]=self.instance.distance_matrix[from_i][to_j]*self.TCov
                
                    mu1=mean_arrival[i]
                    #time_window[self.time_pnt[to_j-self.instance.number_aide]]
                    mu2=visit_time[i+1]  #sequence[i+1].start # visit_time[i+1] 
                
                    sigma1=std_arrival[i]
                    sigma2=0
                
                
                    theta=sigma1
                
                    mean_start[i],std_start[i]=self.approximate_start_time_stats(mu1,mu2,theta,sigma1,sigma2)
                
                else:
                    
                    visit_duration_mean_i=self.instance.list_patient[from_i-self.instance.number_aide].visit_duration
                    visit_duration_std_i=self.SCov*visit_duration_mean_i
                
                    mean_arrival[i]=mean_start[i-1]+visit_duration_mean_i+self.instance.distance_matrix[from_i][to_j]
                
                    variance=std_start[i-1]**2+visit_duration_std_i**2+(self.instance.distance_matrix[from_i][to_j]*self.TCov)**2
                    std_arrival[i]=np.sqrt(variance)
                
                
                    mu1=mean_arrival[i]
                    mu2=visit_time[i+1] #sequence[i+1].start 
                
                
                    sigma1=std_arrival[i]
                    sigma2=0
                    theta=sigma1
                
                    mean_start[i],std_start[i]=self.approximate_start_time_stats(mu1,mu2,theta,sigma1,sigma2)
                
            
            mean_arrival_patient=mean_arrival[-1]
            std_arrival_patient=std_arrival[-1]
                
            
        
        else:
        
            from_i=route[0]
            to_j=route[1]
            mean_arrival_patient=visit_time[0]+self.instance.distance_matrix[from_i][to_j]
            std_arrival_patient=self.instance.distance_matrix[from_i][to_j]*self.TCov
      
                
        print(visit_time[0])        
            
        print(mean_arrival_patient)
        
        print(std_arrival_patient)
        #print(node_id)
        #print("arrival mean for position {} is {} and arrival standard deviation is {}".format(position,mean_arrival[position-1],std_arrival[position-1]))
        return mean_arrival_patient,std_arrival_patient
                
        
        
        
    
    
    
    
        
    