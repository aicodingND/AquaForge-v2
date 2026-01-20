import pandas as pd
import random

def generate_test_roster(team_name, num_swimmers=20):
    """
    Generates a DataFrame with plausible swimmer data for testing.
    """
    
    events = ['50 Free', '100 Free', '200 Free', '500 Free', 
              '100 Back', '100 Breast', '100 Fly', '200 IM']
    
    data = []
    
    # Base times for events (approximate HS level)
    base_times = {
        '50 Free': 24.0, '100 Free': 53.0, '200 Free': 115.0, '500 Free': 310.0,
        '100 Back': 60.0, '100 Breast': 68.0, '100 Fly': 58.0, '200 IM': 130.0
    }
    
    for i in range(1, num_swimmers + 1):
        swimmer_name = f"Test Swimmer {i} ({team_name})"
        gender = random.choice(['M', 'F'])
        grade = random.choice([9, 10, 11, 12])
        
        # Each swimmer swims 2-4 events
        num_events = random.randint(2, 4)
        swimmer_events = random.sample(events, num_events)
        
        for ev in swimmer_events:
            # Add some variance to the time
            # Better swimmers have lower factors
            skill_factor = random.uniform(0.9, 1.2) 
            time = base_times[ev] * skill_factor
            
            # Add small random noise
            time += random.uniform(-1.0, 2.0)
            
            data.append({
                'swimmer': swimmer_name,
                'gender': gender,
                'grade': grade,
                'team': team_name,
                'event': ev,
                'time': round(time, 2),
                'is_relay': False,
                'is_diving': False,
                'dive_score': None
            })
            
    return pd.DataFrame(data)