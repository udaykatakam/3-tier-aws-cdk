from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    aws_sqs as sqs,
    core
)

class MyStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC for ALB
        alb = ec2.Vpc(self,
                     'ALB-VPC', 
                     max_azs= 2,
                     nat_gateways= 1,
                     cidr= '10.0.0.0/24',
                     subnet_configuration= [ec2.SubnetConfiguration(
                                                name="albPublic", subnet_type=ec2.SubnetType.PUBLIC),
                                            ec2.SubnetConfiguration(
                                                name="albPrivate", subnet_type=ec2.SubnetType.PRIVATE),
                     ]
        )

        alb_sg = ec2.SecurityGroup(self, 'alb_sg', vpc=alb, description="Application Load Balancer Security Group", security_group_name= 'alb-sg')
        # alb_sg.add_ingress_rule(ec2.Peer.ipv4('104.5.5.199/32'), connection= ec2.Port.tcp(22))

        # Create VPC for Application Server
        app = ec2.Vpc(self,
                     'APP-VPC', 
                     max_azs= 2,
                     nat_gateways= 1,
                     cidr= '172.16.0.0/24',
                     subnet_configuration= [ec2.SubnetConfiguration(
                                                name="appPrivate", subnet_type=ec2.SubnetType.PRIVATE),
                                            ec2.SubnetConfiguration(
                                                name="appPublic", subnet_type=ec2.SubnetType.PUBLIC),]
        )

        app_sg = ec2.SecurityGroup(self, 'app_sg', vpc=alb, description="Application Security Group", security_group_name= 'app-sg')
        # app_sg.add_ingress_rule(ec2.Peer.ipv4('104.5.5.199/32'), connection= ec2.Port.tcp(22))


        #Create VPC for Database
        data = ec2.Vpc(self,
                     'DATA-VPC', 
                     max_azs= 2,
                     nat_gateways= 1,
                     cidr= '192.168.0.0/24',
                     subnet_configuration= [ec2.SubnetConfiguration(
                                                name="dataPrivate", subnet_type=ec2.SubnetType.PRIVATE),
                                            ec2.SubnetConfiguration(
                                                name="dataPublic", subnet_type=ec2.SubnetType.PUBLIC)]
        )

        data_sg = ec2.SecurityGroup(self, 'data_sg', vpc=alb, description="Database Security Group", security_group_name= 'data-sg')
        # data_sg.add_ingress_rule(ec2.Peer.ipv4('104.5.5.199/32'), connection= ec2.Port.tcp(22))

        peerAlbApp = ec2.CfnVPCPeeringConnection(self, 
                                           'PEERALBAPP',
                                           peer_vpc_id= alb.vpc_id,
                                           vpc_id= app.vpc_id,)
        PeerRoute = 0

        for publicSubnet in alb.public_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= publicSubnet.route_table.route_table_id, 
                                 destination_cidr_block= app.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAlbApp.ref)

        for privateSubnet in alb.private_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= privateSubnet.route_table.route_table_id, 
                                 destination_cidr_block= app.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAlbApp.ref )

        for publicSubnet in app.public_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= publicSubnet.route_table.route_table_id, 
                                 destination_cidr_block= alb.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAlbApp.ref )

        for privateSubnet in app.private_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= privateSubnet.route_table.route_table_id, 
                                 destination_cidr_block= alb.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAlbApp.ref )


        peerAppData = ec2.CfnVPCPeeringConnection(self, 
                                           'PEERAPPDATA',
                                           peer_vpc_id= data.vpc_id,
                                           vpc_id= app.vpc_id,)

        for publicSubnet in app.public_subnets: 
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= publicSubnet.route_table.route_table_id, 
                                 destination_cidr_block= data.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAppData.ref )

        for privateSubnet in app.private_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= privateSubnet.route_table.route_table_id, 
                                 destination_cidr_block= data.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAppData.ref )                               
           
        for publicSubnet in data.public_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                 'PeerRoute' + str(PeerRoute), 
                                 route_table_id= publicSubnet.route_table.route_table_id, 
                                 destination_cidr_block= app.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAppData.ref )

        for privateSubnet in data.private_subnets:
            PeerRoute = PeerRoute + 1
            route = ec2.CfnRoute(self, 
                                'PeerRoute' + str(PeerRoute), 
                                 route_table_id= privateSubnet.route_table.route_table_id, 
                                 destination_cidr_block= app.vpc_cidr_block, 
                                 vpc_peering_connection_id= peerAppData.ref )    
        
        # Create Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(self, 
                                          'ASG', 
                                           instance_type= ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO),  # Need to specify the instance class and size
                                           machine_image= ec2.AmazonLinuxImage(), # Need to Specify the AMI here
                                           vpc= alb, 
                                           desired_capacity= 2,
                                           max_capacity= 2,
                                           min_capacity= 1,
                                           vpc_subnets= ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))
         
        # Create Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, 'alb', vpc= alb, load_balancer_name= 'ALB', internet_facing = True)

        listener = alb.add_listener('Listener', port= 80)

        listener.add_targets('Target', port= 80, targets= [asg])

        listener.connections.allow_default_port_from_any_ipv4('Open to the world');

        asg.scale_on_request_count('AModestLoad', target_requests_per_second= 1)

        # Create ECS Cluster
        cluster =  ecs.Cluster(self, 'ECSCluster', vpc= app )

        fargateService = ecs_patterns.LoadBalancedFargateService(self, "ECSFargateService", 
                                                                 cluster= cluster, 
                                                                 cpu= 512,
                                                                 desired_count= 6,
                                                                 image= ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),
                                                                 memory_limit_mib= 2048,
                                                                 public_load_balancer= True)
        # Setup AutoScaling policy
        scaling = fargateService.service.auto_scale_task_count(
            max_capacity=2
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60),
        )

        core.CfnOutput(
            self, "LoadBalancerDNS",
            value=fargateService.load_balancer.load_balancer_dns_name
        )

        dbCluster = rds.DatabaseCluster(self, 'DatabaseCluster', 
                                        cluster_identifier= 'dbCluster',
                                        engine= rds.DatabaseInstanceEngine.AURORA ,
                                        master_user= rds.Login(username='admin'),
                                        default_database_name='DemoDB',
                                        instance_props=rds.InstanceProps(instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.XLARGE,),
                                                                         vpc=data),)
        aurora_sg = ec2.SecurityGroup(
            self, 'AUPG-SG',
            vpc=data,
            description="Allows PosgreSQL connections from SG",
        )

        cluster.connections.allow_from(aurora_sg, port_range= ec2.Port.tcp(3306))
    


 


       

        




     

 


