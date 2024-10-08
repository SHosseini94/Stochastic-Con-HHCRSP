# -*- coding: utf-8 -*-
"""
Created on Fri May 31 11:30:34 2024

@author: saeed
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 22:05:42 2024

@author: saeed
"""

from Instance import Instance
from Instance_Reader import Instance_Reader
from Simulation import simulation

from gurobipy import *

import os 
import sys 
import getopt
import numpy as np
import ast
import configparser



if __name__=="__main__":
    
    config = configparser.ConfigParser()
    config.read('config.ini')

    delay= int(config['PARAMETERS']['delay'])
    overtime= int(config['PARAMETERS']['overtime'])
    alpha= float(config['PARAMETERS']['alpha'])
    TCov= float(config['PARAMETERS']['TCov'])
    SCov= float(config['PARAMETERS']['SCov'])
    distribution= config['PARAMETERS']['distribution']
    travel_cov= float(config['PARAMETERS']['travel_cov'])
    service_cov= float(config['PARAMETERS']['service_cov'])
    arg_coeff= ast.literal_eval(config['PARAMETERS']['coeff'])
    coeff=np.array(arg_coeff)  #[rainy,clear]
    arg_prob=ast.literal_eval(config['PARAMETERS']['prob'])
    prob=np.array(arg_prob)
    correlation=config['PARAMETERS']['correlation']
    simulation_scenario=int(config['PARAMETERS']['simulation_scenario'])
    iteration= int(config['PARAMETERS']['iteration'])
    case= config['PARAMETERS']['case']

    path= '../data/' + case
    
    os.makedirs(path, exist_ok=True)
        

    
    if (correlation=='yes'):
        from Create_Scenario_Correlation import create_scenario
        from Master_Problem_Correlated import Master_Problem
    else:
        from Create_Scenario import create_scenario
        from Master_Problem import Master_Problem

    
    os.chdir(path)
    
    for f in os.listdir():
        if f.endswith("default.txt"):
            with open(f,'r') as file:
                #print("the instance name is "+f)
                instance=Instance(f)
                instance_reader=Instance_Reader()
                instance_reader.read_instance(file,instance)
                #instance_reader.print_instance(instance)
                if (correlation=='yes'):
                    scenario_normal=create_scenario(instance,simulation_scenario,distribution,travel_cov,service_cov,coeff,prob) #for correlation 
                else:
                    scenario_normal=create_scenario(instance,simulation_scenario,distribution,travel_cov,service_cov) 
    with Env(empty=True) as env:
        env.setParam('OutputFlag',0)
        env.start()
    
        for i in range(iteration):
            
            for f in os.listdir():
                if f.endswith("20_20_new_data.txt") :
                    #print("the instance name is "+f)

                    with open(f,'r') as file:

                        print("the instance name is "+f)
                        instance=Instance(f)
                        instance_reader=Instance_Reader()
                        instance_reader.read_instance(file,instance)
                        for m in range(instance.number_aide,instance.number_node-instance.number_aide):
                            for n in range(instance.number_node-instance.number_aide,instance.number_node):
                                instance.distance_matrix[m][n]=0
                        #instance_reader.print_instance(instance)
                        #scenario_2=create_scenario(instance,nb_scenario,distribution)
                        if (correlation=='yes'):
                            master=Master_Problem(instance,delay,overtime,alpha,TCov,SCov,coeff,prob)
                        else: 
                            master=Master_Problem(instance,delay,overtime,alpha,TCov,SCov)
                            
                        r,obj=master.branch_and_check(env)

                        if obj==0:
                            print("The problem is incomplete")
                        else:
                            print("Finished "+f+" with CPU time {}".format(r))       
                            simulate=simulation()


                            average_total_lateness,average_total_overtime,average_run_lateness,average_run_overtime,max_total_lateness,service_level,mean_service,min_service=simulate.total_delay(instance,scenario_normal,overtime,delay)
                            #file_name=f+"_delay_{}_overtime_{}_alpha_{}_ATCov_{}_ASCov_{}_distribution_{}_correlation_{}_TCov_{}_SCov_{}_{}_approximation_analysis.txt".format(delay,overtime,alpha,TCov,SCov,distribution,correlation,travel_cov,service_cov,i)
                            #save_file_name= os.path.join('../data/result',file_name)
                            path1='../result'
                            os.chdir(path1)
                            with open(f+"_delay_{}_overtime_{}_alpha_{}_ATCov_{}_ASCov_{}_distribution_{}_correlation_{}_TCov_{}_SCov_{}_{}_EVT_analysis.txt".format(delay,overtime,alpha,TCov,SCov,distribution,correlation,travel_cov,service_cov,i),"w") as file:

                                    file.write("\n")
                                    file.write("Method\t"+"EVT-Approximation \n")
                                    file.write("NumSimulationScenario\t{} \n".format(len(scenario_normal.travel_time)))
                                    file.write("Distribution\t"+distribution + "\n")
                                    if (correlation=='yes'):
                                        file.write("Correlation\t"+ correlation +"\t{} \n".format(coeff))
                                    else:
                                        file.write("Correlation\t"+ correlation +"\n")
                                        
                                    #file.write("FixedVisit\t{} \n".format(fixed_visit))
                                    file.write("TravelCov\t{} \n".format(travel_cov))
                                    #file.write("TravelCovMax\t{} \n".format(travel_cov_max))
                                    file.write("ServiceCov\t{} \n".format(service_cov))



                                    file.write("NewPatient\t{} \n".format(len([1 for i in range(instance.number_patient) if instance.list_patient[i].availability==2 ])))

                                    file.write("ActiveAides\t{} \n".format(len([1  for i in range(instance.number_aide) if instance.list_aide[i].availability==2])))

                                    file.write("TotalSolvingTime\t{}\n".format(r))
                                    file.write("AcceptedPatients\t{}\n".format(obj))

                                    file.write("AllowedDelay\t{}\n".format(delay))
                                    file.write("Overtime\t{}\n".format(overtime))
                                    file.write("AssignedServiceLevel/NumberStd\t{}\n".format(alpha))
                                    #file.write("Scenario/Cov\t{}\n".format(TCov))
                                    file.write("Scenario\t{}\n".format(0))
                                    file.write("ApproximationTCov\t{}\n".format(TCov))
                                    file.write("ApproximationSCov\t{}\n".format(SCov))

                                    file.write("AverageTotalLateness\t{}\n".format(average_total_lateness))
                                    file.write("AverageTotalOvertime\t{}\n".format(average_total_overtime))
                                    file.write("AverageRunLateness\t{}\n".format(average_run_lateness))
                                    file.write("AverageRunOvertime\t{}\n".format(average_run_overtime))
                                    file.write("MaximumTotalLateness\t{}\n".format(max_total_lateness))


                                    file.write("RealServiceLevel\t")
                                    file.write(str(service_level))
                                    file.write("\n")

                                    file.write("MeanServiceLevel\t{}\n".format(mean_service))
                                    file.write("MinServiceLevel\t{}\n".format(min_service))
                            path2='../' + case 
                            os.chdir(path2)
    


