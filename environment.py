import os
import pygame
import matplotlib
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt
import random
import time
import numpy as np
import pandas as pd
from car import Car


matplotlib.use('Agg')
matplotlib.use('PS')


total_simulations = 15
pixel_meters_ratio = 0.04
ppu = 30
simulation_time = 30
dt = 0.1
time_threshold = 15

my_seed = 175175175
random.seed(my_seed)
np.random.seed(my_seed)

class Environment:
    def __init__(self, args):
        self.render = not args.no_render
        
        if args.run_idm:
            self.model = 'IDM'
        elif args.run_custom:
            self.model = 'Custom'
        else:
            self.model = 'Test'

        if self.render:
            # initialize the interfaces
            pygame.init()
            pygame.display.set_caption("ITSC 2024 Reproducibility in Transportation Research Tutorial")
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.exit = False
            info_object = pygame.display.Info()
            print("[INFO] Created info_object...")
            self.screen_width = info_object.current_w
            print("[INFO] Set screen_width...")
        else:
            # A dummy screen width to bypass pygame
            self.screen_width = 1000

        self.file_fd = open("flow-density-data", "w")
        self.file_sd = open("flow-speed-data", "w")
        
        # Load the graphs
        self.figure_svd, self.figure_fvd, self.axis_svd, self.axis_fvd = Environment.init_graphs(self)
        self.vehicle_counts = np.random.permutation(np.array([1,2,2,4,7,11,15,18,21,24,30,40,60,80,99]))
        self.simulation_count = 0
        self.trajectory = [] # Trajectory recording the tuple of (car,time,position)


    def init_graphs(self):
        # initialize the graphs
        figure_svd, axis_svd = plt.subplots()
        figure_fvd, axis_fvd = plt.subplots()
        
        axis_svd.plot([], [])
        axis_fvd.plot([], [])

        axis_svd.set(xlabel='Density (veh/m)', ylabel='Speed (m/s)', title='Speed vs Density')

        axis_fvd.set(xlabel='Density (veh/m)', ylabel='Flow (veh/s)', title='Flow vs Density')

        axis_svd.grid()
        axis_fvd.grid()

        return figure_svd, figure_fvd, axis_svd, axis_fvd


    def plot_graph(figure):
        # Generate figure structure on the canvas
        canvas = agg.FigureCanvasAgg(figure)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()

        size = canvas.get_width_height()

        return raw_data, size
        

    def save_data_and_plots(self):
        # Save the two graphs as pngs
        self.figure_svd.savefig('figure_svd.png')
        self.figure_fvd.savefig('figure_fvd.png')
        self.file_fd.close()
        self.file_sd.close()

        # Save the trajectory data of the IDM model
        if self.model == "IDM":
            df_trajectory = pd.DataFrame(self.trajectory, columns = ['Simulation No','Car', 'Time', 'Position'])
            df_trajectory.to_csv('trajectory.csv')


    def run(self):
        # load car image for the visualization
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, "car.png")
        screen_width = self.screen_width
        if self.render:
            car_image = pygame.image.load(image_path)

        svd_x_axis = []
        svd_y_axis = []
        fvd_x_axis = []
        fvd_y_axis = []

        while self.simulation_count < total_simulations:

            self.simulation_count += 1
            time_elapsed = 0
            cars = []

            num_vehicles = self.vehicle_counts[self.simulation_count-1]

            for x in range(0, num_vehicles):
                if x == 0:
                    cars.append(Car((screen_width / ppu - (48 / ppu)) * 0.75, 2, x, screen_width))
                else:
                    cars.append(Car(cars[x - 1].position.x - random.uniform(1, 2), 2, x, screen_width))

            reference_position_x = cars[len(cars) - 1].position.x - 1
            road_length = max((screen_width / ppu - (48 / ppu)) * 0.25,
                              (abs(screen_width / ppu - (48 / ppu)) - reference_position_x))
            info_string = f'[INFO] Running {self.model} Simulation No. {self.simulation_count:>2d} with ' \
                f'{num_vehicles:>2d} vehicles and road length of {road_length:>3.0f} meters.'
            print(info_string)
            density = num_vehicles / (road_length * pixel_meters_ratio)

            flow = 0
            sum_velocity = 0
            velocity_count = 0

            while simulation_time > time_elapsed:

                time_elapsed += dt
                car_previous_positions_x = []

                # Update each vehicle's status
                for x in range(0, len(cars)):
                    if x == 0:
                        car_previous_positions_x.append(cars[0].position.x)
                        cars[x].car_following_model(dt, cars[len(cars) - 1], cars[min(len(cars)-1, 1)],
                        reference_position_x, self.model)
                    elif x < len(cars) -1:
                        car_previous_positions_x.append(cars[x].position.x)
                        cars[x].car_following_model(dt, cars[x - 1], cars[x + 1], reference_position_x, self.model)
                    else:
                        car_previous_positions_x.append(cars[x].position.x)
                        cars[x].car_following_model(dt, cars[x - 1], cars[0], reference_position_x, self.model)
                    self.trajectory.append((self.simulation_count, x,time_elapsed, cars[x].position.x))

                if time_elapsed > time_threshold:
                    for y in range(0, len(cars)):
                        if cars[y].position.x < car_previous_positions_x[y]:
                            flow += 1

                if time_elapsed > time_threshold:
                    for car in cars:
                        sum_velocity += car.velocity.x
                        velocity_count += 1

                if self.render:
                    # Event queue for the simulation
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.exit = True
                        if event.type == pygame.KEYDOWN:
                            # quit the simulation whenever a key is pressed
                            self.save_data_and_plots()
                            pygame.quit()
                            return

                    # Draw the simulation interface
                    self.screen.fill((255, 255, 255))
                    rotated = pygame.transform.rotate(car_image, 0)

                    for x in range(0, len(cars)):
                        self.screen.blit(rotated, cars[x].position * ppu)

                    screen = pygame.display.get_surface()

                    # Draw the svd graph
                    svd_raw_data, svd_size = Environment.plot_graph(self.figure_svd)
                    surf = pygame.image.fromstring(svd_raw_data, svd_size, "RGB")
                    screen.blit(surf, (screen_width / 9, 180))

                    # Draw the fvd graph
                    fvd_raw_data, fvd_size = Environment.plot_graph(self.figure_fvd)
                    surf = pygame.image.fromstring(fvd_raw_data, fvd_size, "RGB")
                    screen.blit(surf, (screen_width / 2, 180))

                    # Add text to interface
                    font = pygame.font.Font('freesansbold.ttf', 16)
                    text = font.render(info_string, True, (0, 0, 0), (255, 255, 255))
                    text_quit = font.render('[X] : Press any key to quit the simulation.',
                                    True, (0, 0, 0), (255, 255, 255))

                    textRect = text.get_rect()
                    textRectQuit = text_quit.get_rect()
                    textRect.center = (400, 25)
                    textRectQuit.center = (400, 50)
                    screen.blit(text, textRect)
                    screen.blit(text_quit, textRectQuit)

                    # Update interface
                    pygame.display.flip()

            # collect data relevant for plotting
            avg_velocity = sum_velocity / velocity_count

            svd_x_axis.append(density)
            svd_y_axis.append(avg_velocity)
            self.axis_svd.scatter(svd_x_axis, svd_y_axis)
            self.file_sd.write(str(density) + "," + str(avg_velocity) + "\n")

            fvd_x_axis.append(density)
            flow_real = flow / (simulation_time - time_threshold)
            fvd_y_axis.append(flow_real)
            self.axis_fvd.scatter(fvd_x_axis, fvd_y_axis)
            self.file_fd.write(str(density) + "," + str(flow_real) + "\n")

        # Save the two graphs as pngs, save the trajectory data for separate plotting
        self.save_data_and_plots()

        if self.render:
            # Wait 5 seconds before closing the display
            time.sleep(5)
