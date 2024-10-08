# -*- coding: utf-8 -*-
"""
Created on Fri May 31 09:46:03 2024

@author: saeed
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 22:21:04 2024

@author: saeed
"""

"""
For each scenario, we create a random number for total time containing 
travel and service time for each combination of two nodes. 

I use poisson distribution with parameter of the sum of travel time 
and service time! 

I can change it later using historical data. 

"""

"""
May 31 2024 

generate correlated scenarios 


"""

import numpy as np




class create_scenario():
    
    def __init__(self,instance,nb_scenario,distribution,Travel_cov,Service_cov,coeff,prob):
        
        self.number_aide=instance.number_aide
        self.number_node=instance.number_node
        self.instance=instance
        travel_matrix=instance.distance_matrix
        number_node=instance.number_node
        number_patient=instance.number_patient
        self.distribution=distribution
        self.coeff=coeff
        self.prob= prob
        
        np.random.seed(10)
        
        weather = np.random.choice(['rainy', 'clear'], size=nb_scenario, p=self.prob)
        self.C_rainy = (weather == 'rainy').astype(int)
        self.C_clear = (weather == 'clear').astype(int)
        
      
        if distribution=="normal":
            self.travel_time={s:[0 if i==j else self.travel_normal_sample(travel_matrix[i][j],travel_matrix[i][j]*Travel_cov,s)
                                 for i in range(number_node)for j in range(number_node)] for s in range(nb_scenario)}
        
            self.service_time={s:[self.normal_sample(self.duration(i),Service_cov*self.duration(i))
                                  for i in range(number_node)] for s in range(nb_scenario)}
        if distribution=="shifted-gamma":
            self.travel_time={s:[0 if i==j else self.gamma_sample(travel_matrix[i][j],Travel_cov)
                                 for i in range(number_node)for j in range(number_node)] for s in range(nb_scenario)}
            
            self.service_time={s:[self.normal_sample(self.duration(i),Service_cov*self.duration(i))
                                  for i in range(number_node)] for s in range(nb_scenario)}
            
        if distribution=="shifted-expo":
            self.travel_time={s:[0 if i==j else self.expo_sample(travel_matrix[i][j],Travel_cov)
                                 for i in range(number_node)for j in range(number_node)] for s in range(nb_scenario)}
            
            self.service_time={s:[self.normal_sample(self.duration(i),Service_cov*self.duration(i))
                                  for i in range(number_node)] for s in range(nb_scenario)}
            
            
        
    
        
            #self.total_time_pmf={s:[0 if i==j else poisson(travel_matrix[i][j]+self.duration(i)).pmf(self.total_time[s][i*number_node+j])
             #                        for i in range(number_node) for j in range(number_node)] for s in range(nb_scenario)}

            # above variable is a flatten version
            


    def duration(self,i):
        if i<self.number_aide or i>=self.number_node-self.number_aide:
            return 0
        else:
            return self.instance.list_patient[i-self.number_aide].visit_duration
    
    def normal_sample(self,mean,std):
        
        if mean==0:
            return 0
        else:
            x=np.random.normal(mean,std)
            
            while (x<0):
                x=np.random.normal(mean,std)
                
        return(x)
        
        
    def travel_normal_sample(self,mean,std,s):
        
        if mean==0:
            return 0
        else:
            x=np.random.normal(mean,std)
            
            while (x<0):
                x=np.random.normal(mean,std)
            
            travel_time= x + self.coeff[0]*x*self.C_rainy[s]+self.coeff[1]*x*self.C_clear[s]
        
        return(travel_time)
    
    def gamma_sample(self,mean,cov,s):
        if mean==0:
            return 0
        else:
            theta=(cov*mean)/2  #the scale parameter of gamma when shape, k, equals to 4 [std(x)=sqrt(shape*theta^2)=mean*cov]
            shifted_mean= (2*cov-1)*mean   # [E(x)=shape*theta] we substance the shifted_mean to finally have the proper mean
            x=np.random.gamma(shape=4,scale=theta)-shifted_mean
            
            while (x<0):
                x=np.random.gamma(shape=4,scale=theta)-shifted_mean
            
            travel_time= x + self.coeff[0]*mean*self.C_rainy[s]+self.coeff[1]*mean*self.C_clear[s]
       
        return(travel_time)
        
    
    
    def expo_sample(self,mean,cov,s):
        if mean==0:
            return 0
        else: 
            rate= 1/(mean*cov)  # lambda or rate at exponential distribution! 
            beta= 1/rate # scale parameter equals to 1\lambda, this equals the std and mean of the distribution 
            shifted_mean= (cov-1)*mean 
            x=np.random.exponential(scale=beta)-shifted_mean
            
            while (x<0):
                x=np.random.exponential(scale=beta)-shifted_mean
            
            travel_time= x + self.coeff[0]*mean*self.C_rainy[s]+self.coeff[1]*mean*self.C_clear[s]
        
        return(travel_time)
                
        #if x>0 else self.normal_sample(mean,std)

