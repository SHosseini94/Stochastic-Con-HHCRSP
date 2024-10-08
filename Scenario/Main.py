# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 22:05:42 2024

@author: saeed
"""

from Instance import Instance
from Instance_Reader import Instance_Reader
#from Create_Scenario import create_scenario
#from Create_Scenario_Correlation import create_scenario
from Master_Problem import Master_Problem
#from Master_Problem_SoftPersonCon import Master_Problem
from Simulation import simulation

from gurobipy import *

import os 
import sys 
import getopt
import ast

import configparser
import numpy as np



def myfunc(argv):
    arg_nb_scenario=None
    arg_delay=None
    arg_overtime=None
    arg_alpha=None
    arg_distribution=None
    arg_travel_cov=None
    arg_service_cov=None
    arg_coeff=None #[rainy, clear]
    arg_prob=None # [rainy,clear] 
    arg_correlation=None
    
    
    arg_help="{0} -n <nb_scenario> -d <delay> -o <overtime> -a <alpha> -di <distribution> -tc <travel_cov> -sc <service_cov> -cf <coeff [rainy,clear]> -pr <prob [rainy,clear]> -cr <correlation>".format(argv[0])
    
    
    try:
        opts,args=getopt.getopt(argv[1:],"hn:d:o:a:di:tc:sc:cf:pr:cr:",["help","nb_scenario=","delay=","overtime=","alpha=","distribution=",
                                                                       "travel_cov=","service_cov=","coeff=","prob=","correlation="])
    except:
        print(arg_help)
        sys.exit(2)
    
    
    for opt,arg in opts:
        if opt in ("-h","--help"):
            print(arg_help) 
            sys.exit(2)
        elif opt in ("-n","--nb_scenario"):
            arg_nb_scenario=int(arg)
            #print(arg_nb_scenario)
        elif opt in ("-d","--delay"):
            arg_delay=int(arg)
            #print(arg_delay)
        elif opt in ("-o","--overtime"):
            arg_overtime=int(arg)
            #print(arg_overtime)
        elif opt in ("-a","--alpha"):
            arg_alpha=float(arg)
            #print(arg_alpha)
    
        elif opt in ("-di","--distribution"):
            arg_distribution=arg
            #print(arg_distribution)
        elif opt in ("-tc","--travel_cov"):
            arg_travel_cov=float(arg)
            #print(arg_travel_cov_min)
            #print(arg_travel_cov_max)
        elif opt in ("-sc","--service_cov"):
            arg_service_cov=float(arg)
            #print(arg_service_cov)
        elif opt in ("-cf","--coeff"):
            if arg!=None:
                arg_coeff=ast.literal_eval(arg)
            else:
                arg_coeff=arg
        elif opt in ("-pr","--prob"):
            if arg!=None:
                arg_prob=ast.literal_eval(arg)
            else:
                arg_prob=arg
        elif opt in ("-cr","--correlation"):
            arg_correlation=arg        
    
    
    print('nb_scenario: {}'.format(arg_nb_scenario))
    print('delay: {}'.format(arg_delay))
    print('overtime: {}'.format(arg_overtime))
    print('alpha: {}'.format(arg_alpha))
    #print('Cov: {}'.format(arg_Cov))
    print('distribution: {}'.format(arg_distribution))
    print('Travel_Cov: {}'.format(arg_travel_cov))
    #print('Travel_Cov_max: {}'.format(arg_travel_cov_max))
    print('Service_Cov: {}'.format(arg_service_cov))
    print('coeff: {}'.format(arg_coeff))
    print('prob: {}'.format(arg_prob))
    print('correlation: {}'.format(arg_correlation))
    

    
    return arg_nb_scenario,arg_delay,arg_overtime,arg_alpha,arg_distribution,arg_travel_cov,arg_service_cov,arg_coeff,arg_prob,arg_correlation


# In[ ]:


if __name__=="__main__":

    config = configparser.ConfigParser()
    config.read('config.ini')
    
    nb_scenario=int(config['PARAMETERS']['nb_scenario'])
    delay= int(config['PARAMETERS']['delay'])
    overtime= int(config['PARAMETERS']['overtime'])
    alpha= float(config['PARAMETERS']['alpha'])
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
    else:
        from Create_Scenario import create_scenario
    
    
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
                    scenario_normal=create_scenario(instance,simulation_scenario,distribution,travel_cov,service_cov) #shifted-gamma

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
                        #instance_reader.print_instance(instance)
                        if (correlation=='yes'):
                            scenario_2=create_scenario(instance,nb_scenario,distribution,travel_cov,service_cov,coeff,prob)  #for correlation
                        else:
                            scenario_2=create_scenario(instance,nb_scenario,distribution,travel_cov,service_cov)
                            
                        master=Master_Problem(instance,scenario_2,delay,overtime,alpha)
                        r,obj=master.branch_and_check(env)



                        if obj==0:
                            print("The problem is incomplete")
                        else:
                            print("Finished "+f+" with CPU time {}".format(r))

                            simulate=simulation()




                            average_total_lateness,average_total_overtime,average_run_lateness,average_run_overtime,max_total_lateness,service_level,mean_service,min_service=simulate.total_delay(instance,scenario_normal,overtime,delay)
                            
                            path1='../result'
                            os.chdir(path1)

                            with open(f+"_delay_{}_overtime_{}_alpha_{}_NbScenario_{}_distribution_{}_correlation_{}_TCov_{}_SCov_{}_{}_scenario_analysis.txt".format(delay,overtime,alpha,nb_scenario,distribution,correlation,travel_cov,service_cov,i),"w") as file:

                                    #file.write("........................\n")
                                    file.write("\n")
                                    file.write("Method\t"+"Scenario \n")
                                    #file.write("the instance name is " +f+"\n")
                                    file.write("NumSimulationScenario\t{} \n".format(len(scenario_normal.travel_time)))
                                    file.write("Distribution\t"+ distribution +"\n")
                                    
                                    if (correlation=="yes"):
                                        file.write("Correlation\t"+ correlation +"\t{} \n".format(coeff))
                                    else:
                                        file.write("Correlation\t"+ correlation +"\n")

                                    file.write("TravelCov\t{} \n".format(travel_cov))
                                    file.write("ServiceCov\t{} \n".format(service_cov))

                                    file.write("NewPatient\t{} \n".format(len([1 for i in range(instance.number_patient) if instance.list_patient[i].availability==2 ])))

                                    file.write("ActiveAides\t{} \n".format(len([1  for i in range(instance.number_aide) if instance.list_aide[i].availability==2])))

                                    file.write("TotalSolvingTime\t{}\n".format(r))
                                    file.write("AcceptedPatients\t{}\n".format(obj))

                                    file.write("AllowedDelay\t{}\n".format(delay))
                                    file.write("Overtime\t{}\n".format(overtime))
                                    file.write("AssignedServiceLevel/NumberStd\t{}\n".format(alpha))
                                    file.write("Scenario\t{}\n".format(len(scenario_2.travel_time)))
                                    file.write("ApproximationTCov\t{}\n".format(0))
                                    file.write("ApproximationSCov\t{}\n".format(0))

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
