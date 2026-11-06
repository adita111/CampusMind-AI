
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  CampusService,
  Building,
  Floor,
  Room,
  SensorReading,
  ScheduledActivity,
  OptimizationResult
} from './services/campus.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  private campusService = inject(CampusService);

  buildings: Building[] = [];
  floors: Floor[] = [];
  rooms: Room[] = [];

  selectedBuilding = '';
  selectedFloor: number | null = null;
  selectedRoom: Room | null = null;

  sensorReading: SensorReading | null = null;
  schedule: ScheduledActivity[] = [];

  loading = false;
  error = '';

  optimizationResult: OptimizationResult | null = null;
optimizing = false;
optimizationError = '';

  ngOnInit(): void {
    this.loadBuildings();
  }

  loadBuildings(): void {
    this.campusService.getBuildings().subscribe({
      next: (data) => {
        this.buildings = data;

        if (data.length > 0) {
          this.selectBuilding(data[0].id);
        }
      },
      error: () => {
        this.error = 'Could not load buildings';
      }
    });
  }

  selectBuilding(buildingId: string): void {
    this.selectedBuilding = buildingId;
    this.selectedFloor = null;
    this.selectedRoom = null;
    this.rooms = [];
    this.floors = [];

    this.campusService.getFloors(buildingId).subscribe({
      next: (data) => {
        this.floors = data;

        if (data.length > 0) {
          this.selectFloor(data[0].number);
        }
      },
      error: () => {
        this.error = 'Could not load floors';
      }
    });
  }

  selectFloor(floorNumber: number): void {
    this.selectedFloor = floorNumber;
    this.selectedRoom = null;
    this.sensorReading = null;
    this.schedule = [];

    this.campusService.getRooms(
      this.selectedBuilding,
      floorNumber
    ).subscribe({
      next: (data) => {
        this.rooms = data;

        if (data.length > 0) {
          this.selectRoom(data[0]);
        }
      },
      error: () => {
        this.error = 'Could not load rooms';
      }
    });
  }

  selectRoom(room: Room): void {
    this.selectedRoom = room;
    this.sensorReading = null;
    this.schedule = [];

    this.refreshRoom();
  }

  refreshRoom(): void {
    const room = this.selectedRoom;

    if (!room) {
      return;
    }

    this.loading = true;
    this.error = '';

    this.campusService.getRoomSensors(room.id).subscribe({
      next: (sensors) => {
        const tempSensor = sensors.find(
          sensor => sensor.sensor_type === 'temperature'
        );

        if (tempSensor) {
          this.campusService
            .getSensorReading(tempSensor.id)
            .subscribe({
              next: (reading) => {
                if (this.selectedRoom?.id === room.id) {
                  this.sensorReading = reading;
                }
                this.loading = false;
              },
              error: () => {
                this.loading = false;
                this.error = 'Could not load temperature';
              }
            });
        } else {
          this.loading = false;
        }
      },
      error: () => {
        this.loading = false;
        this.error = 'Could not load sensors';
      }
    });

    this.campusService.getRoomSchedule(room.id).subscribe({
      next: (data) => {
        if (this.selectedRoom?.id === room.id) {
          this.schedule = data;
        }
      },
      error: () => {
        this.error = 'Could not load schedule';
      }
    });

    
  }

  
runOptimization(): void {
  this.optimizing = true;
  this.optimizationError = '';
  this.optimizationResult = null;

  this.campusService.optimizeSchedule().subscribe({
    next: (result) => {
      this.optimizationResult = result;
      this.optimizing = false;

      console.log('Optimization result:', result);
    },
    error: (error) => {
      this.optimizing = false;

      this.optimizationError =
        error.error?.detail || 'Schedule optimization failed';

      console.error('Optimization error:', error);
    }
  });
}

}
