# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 23:47:08 2024

@author: saeed
"""



from gurobipy import *
import os 
import time
import sys

from Subproblem import Subproblem
#from Subproblem_fixedVisitTime import Subproblem   # if we want to fix visit time for existing patient 

def lazy_callback(model,where):
    
    if where==GRB.Callback.MIPSOL:
        model._call+=1
           
        yval=model.cbGetSolution(model._yvars)
        
        list_Pik={k.id:{d:[i for kk,i in model._assignment.select(k.id,'*') if yval[kk,i,d]>0.5] for d in 
                                 range(model._instance.horizon)} for k in model._activeAides}
        obj = model.cbGet(GRB.Callback.MIPSOL_OBJBST)
        
        #print("the objective is {}".format(obj))
        #print("the list of Pik is:")
        #print(list_Pik)
        
        Solve={k.id:0 for k in model._activeAides}
        
        for k in Solve:
            for d in range(model._instance.horizon):
                if len(list_Pik[k][d])>0:
                    Solve[k]=1
                    break
        for k in model._activeAides:
            if Solve[k.id]==1:
                
                new_patient=False
                l=[set(list_Pik[k.id][d]) for d in range(model._instance.horizon)]
                union_patients=list(set().union(*l))
                union_patients.sort()
                value=""
                for id in union_patients:
                    value+=str(id)+"-"
                
                
                assignment_pattern=[]    #added 22/11/05
                for d in range(model._instance.horizon):
                    if list_Pik[k.id][d] not in assignment_pattern and list_Pik[k.id][d]:
                        assignment_pattern.append(list_Pik[k.id][d])
                        
                number_pattern=len(assignment_pattern)
                value=""
                for d in range(number_pattern):
                    for b in assignment_pattern[d]:
                        value+=str(b)+"-"
                    value+="/"
                    
                    
                for i in union_patients:
                    if model._instance.list_patient[i].availability==2:
                        new_patient=True
                        break
                
                if value not in model._instance.list_feasible_per_aide[k.id] and new_patient:
                    
                    #print("the assigned patients to aide {}".format(k.id+1))
                    #print(list_Pik[k.id])
                    subproblem=Subproblem(model._instance,k.id,list_Pik[k.id],model._maximum_delay,model._overtime, model._alpha,model._TCov,model._SCov)
                    model._subcall+=1
                    cut=[]
                    list_feasible_day_per_aide=[[None] for i in range(20)]
                    start=time.time()
                    time_limit,status,solve_complete_sub,list_cut=subproblem.generate_cut(list_feasible_day_per_aide,cut,False)
                    end=time.time()
                    total_time=end-start
                    model._subTime+=total_time
                    if solve_complete_sub==1:
                        model._complete_sub+=1  #increase the number of sub-problem solve completely
                        if status==False:
                            model._inf_complete_sub+=1   # increase the number of sub-problems solve completely and are infeasible
                            if time_limit==True:
                                model._time_limit+=1  # increase the number of subproblem reach time limit in CP 
                                
                        
                    #print("the list of cut is:")
                    #print(list_cut)
                
                    if len(list_cut[0][1])>0:
                        model.cbLazy(quicksum((1-model._yvars[k.id,i,d]) for i,d in list_cut[0][1])>=1)
                        
                        #print(quicksum((1-model._yvars[k.id,i,d]) for i,d in list_cut[0][1])>=1)
                        model._nblazy+=1 
    


class Master_Problem():
    
    def __init__(self,instance,l,overtime,alpha,TCov,SCov):
        
        #print("Master Problem is created")
        
        self.instance=instance
        self.maximum_delay=l
        self.overtime=overtime
        self.alpha=alpha
        self.TCov=TCov
        self.SCov=SCov
        self.nb_aide=instance.number_aide  
        #print("number_aide:{}".format(self.nb_aide))
        self.fixed_patient=[instance.list_patient[i] for i in range(instance.number_patient) if instance.list_patient[i].
                            availability==1] 
        #print("the number of fixed patients is: {}".format(len(self.fixed_patient)))
        
        self.free_patient=[instance.list_patient[i] for i in range(instance.number_patient) if instance.list_patient[i].
                            availability==2]
        #print("the number of free patients is: {}".format(len(self.free_patient)))
        self.fixed_aide=[instance.list_aide[i] for i in range(instance.number_aide) if instance.list_aide[i].
                            availability==1]
        #print("the number of fixed aides is: {}".format(len(self.fixed_aide)))
        self.active_aide=[instance.list_aide[i] for i in range(instance.number_aide) if instance.list_aide[i].
                            availability==2]
        #print("the number of active aides is: {}".format(len(self.active_aide)))
        self.nb_patient=len(self.fixed_patient)+len(self.free_patient)   #??? 
        #print("the number of available patietns is {}".format(self.nb_patient))

        self.horizon=instance.horizon
        
        #print("the horizon of problem is {}".format(self.horizon))
        
        self.current_assignment=tuplelist([(i.pre_assigned_aide,i.id) for i in self.fixed_patient])
        #print("the fixed patient-aide assignments:")
        #print(self.current_assignment)
        self.new_assignment=tuplelist([(k.id,i.id) for k in self.active_aide for i in self.free_patient])
        #print("the potential patient-aide assignment") 
        #print(self.new_assignment)
        self.all_assignment=self.current_assignment+self.new_assignment
        #print("all assignments:")
        #print(self.all_assignment)
        
        self.morning_patient=[i for i in range(instance.number_patient) if instance.list_patient[i].availability!=0
                             and instance.list_patient[i].time_window[1]<=72]
        self.evening_patient=[i for i in range(instance.number_patient) if instance.list_patient[i].availability!=0
                             and instance.list_patient[i].time_window[0]>=72]
        
        self.ugmentedDurationFrom={(k,i,d):self.instance.list_patient[i].visit_duration for k,i in self.all_assignment for d in range
                                  (self.horizon)}
        #print(self.ugmentedDurationFrom)
        
        self.ugmentedDurationTo={(k,i,d):self.instance.list_patient[i].visit_duration for k,i in self.all_assignment for d in range
                                  (self.horizon)}
        #print(self.ugmentedDurationTo)
        for k,i in self.all_assignment:
            
            location_start=self.instance.list_aide[k].location_start
            location_end=self.instance.list_aide[k].location_end
            if (k,i) in self.current_assignment:
                #current patient 
                for d in range(self.horizon):
                    if self.instance.list_patient[i].pre_assigned_day[d]==1:  #this patient i is pre-assigned 
                        
                        #Travel time from previous 
                        minTravelTime=self.instance.distance_matrix[location_start][i+self.nb_aide]  #travel from start base to patient 
                        for j in range(self.nb_patient):
                            # this patient j is also pre-assigned
                            if j!=i and (k,j) in self.current_assignment and self.instance.list_patient[j].pre_assigned_day[d]==1 and self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]<minTravelTime:
                                minTravelTime=self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]
                                #print(j+self.nb_aide)
                                continue
                             #this patient j is not already assigned 
                            elif j!=i and (k,j) in self.new_assignment and self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]<minTravelTime:
                                minTravelTime=self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]
                                #print(j+self.nb_aide)
                        self.ugmentedDurationFrom[k,i,d]+=minTravelTime 
                        #print("min travel from")
                        #print (k,i,d)
                        #print(minTravelTime)
                        #Travel time to next 
                        minTraveltime=self.instance.distance_matrix[i+self.nb_aide][location_end]
                        for j in range(self.nb_patient):
                            # this patient j is also pre-assigned 
                            if j!=i and (k,j) in self.current_assignment and self.instance.list_patient[j].pre_assigned_day[d]==1 and self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]<minTravelTime:
                                minTravelTime=self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]
                                #print(j+self.nb_aide)
                                continue
                            #this patient j is not already assigned
                            elif j!=i and (k,j) in self.new_assignment and self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]<minTravelTime:
                                minTravelTime=self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]
                                #print(j+self.nb_aide)
                        self.ugmentedDurationTo[k,i,d]+=minTravelTime 
                        #print("min travel to ")
                        #print (k,i,d)
                        #print(minTravelTime)
            else:  #new patient 
                for d in range(self.horizon):
                    #Travel time from previous
                    minTravelTime=self.instance.distance_matrix[location_start][i+self.nb_aide]
                    for j in range(self.nb_patient):
                        # this patient j is also pre-assigned 
                        if j!=i and (k,j) in self.current_assignment and self.instance.list_patient[j].pre_assigned_day[d]==1 and self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]<minTravelTime:
                            minTravelTime=self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]
                            #print(j+self.nb_aide)
                            continue
                        #this patient j is not already assigned 
                        elif j!=i and (k,j) in self.new_assignment and self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]<minTravelTime:
                            minTravelTime=self.instance.distance_matrix[j+self.nb_aide][i+self.nb_aide]
                            #print(j+self.nb_aide)
                    
                    self.ugmentedDurationFrom[k,i,d]+=minTravelTime 
                    #print("mint travel from")
                    #print (k,i,d)
                    #print(minTravelTime)    
                    #Travel time to next 
                    minTraveltime=self.instance.distance_matrix[i+self.nb_aide][location_end]
                    for j in range(self.nb_patient):
                        # this patient j is also pre-assigned 
                        if j!=i and (k,j) in self.current_assignment and self.instance.list_patient[j].pre_assigned_day[d]==1 and self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]<minTravelTime:
                            minTravelTime=self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]
                            #print(j+self.nb_aide)
                            continue
                        #this patient j is not already assigned
                        elif j!=i and (k,j) in self.new_assignment and self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]<minTravelTime:
                            minTravelTime=self.instance.distance_matrix[i+self.nb_aide][j+self.nb_aide]
                            #print(j+self.nb_aide)
                    self.ugmentedDurationTo[k,i,d]+=minTravelTime 
                    #print("min travel to ")
                    #print (k,i,d)
                    #print(minTravelTime)     
                    
                            
    
    """ It is a function to call the subproblem 
        when the master problem finds a feasible solution 
        and add feasibility cuts when they are required.
        It links the master and subproblem. 
    """
    
    
        
    def branch_and_check(self,env):
        
        
            
        with Model(env=env) as m:

            #m=Model('Heching_master')


            delta=m.addVars(self.nb_patient,vtype=GRB.BINARY,name="delta")

            x=m.addVars(self.all_assignment,vtype=GRB.BINARY, name="x")
            y=m.addVars(self.all_assignment,self.horizon,vtype=GRB.BINARY, name="y")

            m.setObjective(quicksum(delta[i] for i in range(self.nb_patient)), GRB.MAXIMIZE)


            m.addConstrs((quicksum(x[k,i] for k,i in self.all_assignment.select('*',ii))-delta[ii]==0 for ii in 
                          range(self.nb_patient)),"driverCon")

            m.addConstrs((y[k,i,d]<=x[k,i] for k,i in self.all_assignment for d in range(self.horizon)),"daily_assignment")

            m.addConstrs((quicksum(y[k,i,d] for k,i in self.all_assignment.select('*',ii) for d in range(self.horizon))==
                         self.instance.list_patient[ii].number_visit*delta[ii] for ii in range(self.nb_patient)),"number_visit_days")

            m.addConstrs((x[k,i]==1 for k,i in self.current_assignment),"current_patient_assignment")

            m.addConstrs((delta[i]==1 for k,i in self.current_assignment),"accept_current_patient")

            m.addConstrs((y[k,i,d]==self.instance.list_patient[i].pre_assigned_day[d] for d in range(self.horizon) for k,i 
                         in self.current_assignment),"current_patient_daily_assignment")


            for k,i in self.new_assignment:
                if self.instance.list_patient[i].code_value!=0:
                    m.addConstrs((y[k,i,d]+y[k,i,d+v]<=1 for d in range(self.horizon) for v in range(1,self.instance.list_patient[i].code_value+1)
                                 if d+v<=(self.horizon-1)))


            m.addConstrs((quicksum(y[k,i,d]*self.ugmentedDurationFrom[k,i,d] for k,i in self.all_assignment.select(kk,'*') 
                                   if i in self.morning_patient)<=72-self.instance.list_aide[kk].time_window_start[0] for d in range(self.horizon) for kk in range(self.nb_aide)),"morning_time")

            m.addConstrs((quicksum(y[k,i,d]*self.ugmentedDurationTo[k,i,d] for k,i in self.all_assignment.select(kk,'*') if i in 
                                   self.evening_patient)<=self.instance.list_aide[kk].time_window_end[1]-72 for kk in range(self.nb_aide) for d in range(self.horizon)),"evening_time")

            #extra time_window constraints >>>it makes the solving time worse 

            """
            m.addConstrs((y[k,i,d]==0 for d in range(self.horizon) for k,i in self.all_assignment 
                          if self.instance.list_aide[k].time_window_start[0]+self.ugmentedDurationFrom[k,i,d]>self.instance.list_patient[i].time_window[1]),"time_window_morning")


            m.addConstrs((y[k,i,d]==0 for d in range(self.horizon) for k,i in self.all_assignment 
                          if self.instance.list_patient[i].time_window[0]+self.ugmentedDurationTo[k,i,d]>self.instance.list_aide[k].time_window_end[1]),"time_window_evening")

            m.addConstrs((quicksum(x[k,i]*(self.instance.list_patient[i].visit_duration)*(self.instance.list_patient[i].number_visit)
                                   for k,i in self.all_assignment.select(kk,'*'))<=self.instance.list_aide[kk].maximum_work_time for kk in range(self.nb_aide)),"over_time")

            """
            #m.write("heching-master.lp")self.instance.list_aide[k].time_window_end[0]


            m._yvars = y
            m._instance=self.instance
            m._activeAides=self.active_aide
            m._assignment=self.all_assignment
            m._call=0
            m._nblazy=0
            m._subcall=0
            m._subTime=0
            m._complete_sub=0
            m._inf_complete_sub=0
            m._time_limit=0
            #m._scenario=create_scenario(self.instance,self.nb_scenario)
            m._maximum_delay=self.maximum_delay
            m._overtime=self.overtime
            m._alpha=self.alpha
            m._TCov=self.TCov
            m._SCov=self.SCov
            m.setParam("LazyConstraints",1)
            m.setParam("TimeLimit",7200)
            m.setParam("Presolve",0)
            m.setParam("Threads",1)
            #m.setParam("Heuristics",0)
            #m.setParam("LogFile","log_file_master_approx.txt")
            #m.write("heching-master_approx.lp")
            m.optimize(lazy_callback)
            if m.status == GRB.OPTIMAL:

                #print("the number of lazy constraint: {}".format(m._nblazy))
                #print("the run time is: {}".format(m.Runtime))
                #m.printAttr('X')
                f={k:{d:[i for kk,i in self.all_assignment.select(k,'*') if y[kk,i,d].getAttr('X')>0.5] for d in 
                                         range(self.horizon)} for k in range(self.nb_aide)}



                Solve={k.id:0 for k in self.active_aide}

                for k in Solve:
                    for d in range(self.instance.horizon):
                        if len(f[k][d])>0:
                            Solve[k]=1
                            break
                for k in self.active_aide:

                    if Solve[k.id]==1:

                        new_patient=False
                        l=[set(f[k.id][d]) for d in range(self.instance.horizon)]
                        union_patients=list(set().union(*l))
                        union_patients.sort()

                        for i in union_patients:
                            if self.instance.list_patient[i].availability==2:
                                new_patient=True
                                break

                        if new_patient:
                            subproblem=Subproblem(self.instance,k.id,f[k.id],self.maximum_delay,self.overtime,self.alpha,self.TCov,self.SCov)
                            cut=[]
                            list_feasible_day_per_aide=[[None] for i in range(self.instance.number_aide)]
                            list_cut=subproblem.generate_cut(list_feasible_day_per_aide,cut,True)


                for i in range(self.nb_patient):
                    if delta[i].getAttr('X')>0.1:
                        for kk,ii in self.all_assignment.select('*',i):
                            if x[kk,ii].getAttr('X')>0.1:
                                self.instance.list_patient[i].pre_assigned_aide=kk
                                for d in range(self.horizon):
                                    if y[kk,ii,d].getAttr('X')>0.1:
                                        self.instance.list_patient[i].pre_assigned_day[d]=1
                                    else:
                                        self.instance.list_patient[i].pre_assigned_day[d]=0
                    else:
                        self.instance.list_patient[i].pre_assigned_aide=-1
                        for d in range(self.horizon):
                            self.instance.list_patient[i].pre_assigned_day[d]=0
                        self.instance.list_patient[i].visit_time=0

                #self.write_solution(m.getObjective().getValue(),m._call,m._nblazy,m._subcall,m._complete_sub,m._inf_complete_sub,m._time_limit,m.Runtime,m._subTime)
                return m.Runtime,m.getObjective().getValue()
            elif m.status == GRB.TIME_LIMIT:
                print("Time limit reached for master problem")
                return 7200, 0
            elif m.status ==GRB.INFEASIBLE:
                print("The problem is infeasible")
                return 0, 0
                        
                                    
                        
        
        
        
    
    def write_solution(self,obj,nbcall,nblazy,subcall,complete_sub,inf_sub,time_limit,comp_time,sub_time):
        
        
        with open("output_approx.txt","a") as f:
            f.write("----------------------------------------------------------------\n")
            f.write(self.instance.instance_name)
            f.write('\n')
            f.write("Method ArrivalApproximation \n")
            f.write("NewPatients {}\n".format(len(self.free_patient)))
            f.write("ActiveAides {}\n".format(len(self.active_aide)))
            f.write("TCov {}\n".format(self.TCov))
            f.write("SCov {}\n".format(self.SCov))
            
            f.write("MaximumAllowedDelay {}\n".format(self.maximum_delay))
            f.write("ServiceLevel {}\n".format(self.alpha))
            f.write("AcceptedPatients {} \n".format(obj))
            f.write("CallbackCall {}".format(nbcall))
            f.write('\n')
            f.write("LazyCut {}".format(nblazy))
            f.write('\n')
            f.write("SubproblemCall {}".format(subcall))
            f.write('\n')
            f.write("SubproblemsSolvedCompletely {} \n".format(complete_sub))
            f.write("CompleteSubproblemsInfeasible {} \n".format(inf_sub))
            f.write("InfeasibleSubproblemsReachingTimeLimit {} \n".format(time_limit))
            f.write("TotalSolvingTime {} \n".format(comp_time))
            f.write("TotalSolvingTimeSubproblems {}\n".format(sub_time))
            
            
            f.write("patient_id,aide_id,visit_time,is_visited_day_1,is_visited_day_2,is_visited_day_3,is_visited_day_4,is_visited_day_5")
            f.write('\n')
            for i in range(self.nb_patient):
                f.write(str(self.instance.list_patient[i].id)+','+str(self.instance.list_patient[i].pre_assigned_aide)+
                        ','+str(self.instance.list_patient[i].visit_time)+','+
                        str(self.instance.list_patient[i].pre_assigned_day[0])+','+str(self.instance.list_patient[i].pre_assigned_day[1])+','+
                       str(self.instance.list_patient[i].pre_assigned_day[2])+','+str(self.instance.list_patient[i].pre_assigned_day[3])+','+
                       str(self.instance.list_patient[i].pre_assigned_day[4]))
                f.write('\n')
                
        #"""

        with open("change_approx.txt","a") as f:
            f.write("----------------------------------------------------------------\n")
            f.write(self.instance.instance_name+'\n')
            f.write("preAssignNurse \n")
            for i in range(self.nb_patient):
                f.write(str(int(self.instance.list_patient[i].pre_assigned_aide)+1)+' ')
            f.write('\n')
            f.write("preAssignDays \n")
            for i in range(self.nb_patient):
                f.write(str(self.instance.list_patient[i].pre_assigned_day[0])+' '
                        +str(self.instance.list_patient[i].pre_assigned_day[1])+' '
                        +str(self.instance.list_patient[i].pre_assigned_day[2])+' '
                        +str(self.instance.list_patient[i].pre_assigned_day[3])+' '
                        +str(self.instance.list_patient[i].pre_assigned_day[4])+'\n')
            f.write("preAssignWindows \n")
            for i in range(self.nb_patient):
                f.write(str(self.instance.list_patient[i].visit_time)+
                        ' '+
                        str(int(self.instance.list_patient[i].visit_time)+int(self.instance.list_patient[i].visit_duration))+'\n')
            
                
            
        with open("route_approx.txt","a") as f:
            f.write("----------------------------------------------------------------\n")
            f.write(self.instance.instance_name)
            f.write('\n')
            f.write("Method ArrivalApproximation \n")
            
            for i in self.active_aide:
                f.write('Aide {}'.format(i.id))
                f.write('\n')
                for d in range(len(i.route)):
                    f.write('Route_{}'.format(d+1))
                    f.write('\n')
                    f.write(str(i.route[d]))
                    f.write('\n')
        
        with open("schedule_approx.txt","a") as f:
            f.write("----------------------------------------------------------------\n")
            f.write(self.instance.instance_name)
            f.write('\n')
            f.write("Method ArrivalApproximation \n")
            
            for i in self.active_aide:
                f.write('Aide {}'.format(i.id))
                f.write('\n')
                for d in range(len(i.schedule)):
                    f.write('Schedule_{}'.format(d+1))
                    f.write('\n')
                    f.write(str(i.schedule[d]))
                    f.write('\n')
                
                    
                    
        with open("Route-Schedule_approx.txt","a") as f:
            
            f.write("----------------------------------------------------------------\n")
            f.write(self.instance.instance_name)
            f.write('\n')
            f.write("Method ArrivalApproximation \n")
            
            for i in self.active_aide:
                for d in range(len(i.route)):
                    f.write(str(i.route[d]))
                    f.write('\n')
                    f.write(str(i.schedule[d]))
                    f.write('\n')
                    f.write('\n')
                f.write('\n')
                    
                    

            
        
        #"""
    
    
   
            
        
        
        
        