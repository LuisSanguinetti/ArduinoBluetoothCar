import numpy as np
import matplotlib.pyplot as plt
from environment import CarSimulatorEnv
from agent import DQNAgent
import os

def train_agent(episodes=500, render_interval=50):
    """Train the DQN agent"""
    
    # Create environment and agent turned to 8 again so that i need to figure out how to give it the back button without the backwards to avoid trapping
    env = CarSimulatorEnv(render=False)
    agent = DQNAgent(state_size=4, action_size=8, lr=0.001)
    
    # Training metrics
    scores = []
    avg_scores = []
    
    # Create models directory
    os.makedirs('trained_models', exist_ok=True)
    
    for episode in range(episodes):
        # Toggle rendering for some episodes
        if episode % render_interval == 0:
            env.render_mode = True
        else:
            env.render_mode = False
            
        state = env.reset()
        total_reward = 0
        done = False
        
        while not done:
            # Choose action
            action = agent.act(state, training=True)
            
            # Take action
            next_state, reward, done, _ = env.step(action)
            
            # Store experience
            agent.remember(state, action, reward, next_state, done)
            
            # Update state
            state = next_state
            total_reward += reward
            
            # Train agent
            if len(agent.memory) > agent.batch_size:
                agent.replay()
        
        # Update target network every 10 episodes
        if episode % 10 == 0:
            agent.update_target_network()
        
        # Record scores
        scores.append(total_reward)
        avg_score = np.mean(scores[-100:])
        avg_scores.append(avg_score)
        
        print(f"Episode {episode+1}/{episodes}, "
              f"Score: {total_reward:.2f}, "
              f"Avg Score: {avg_score:.2f}, "
              f"Epsilon: {agent.epsilon:.3f}, "
              f"Distance: {env.total_distance:.1f}")
        
        # Save model periodically
        if (episode + 1) % 100 == 0:
            agent.save(f'trained_models/car_agent_episode_{episode+1}.pth')
    
    # Save final model
    agent.save('trained_models/car_agent_final.pth')
    
    # Plot training progress
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(scores)
    plt.plot(avg_scores)
    plt.title('Training Scores')
    plt.xlabel('Episode')
    plt.ylabel('Score')
    plt.legend(['Score', 'Average Score'])
    
    plt.subplot(1, 2, 2)
    plt.plot([i*agent.epsilon_decay**i for i in range(len(scores))])
    plt.title('Epsilon Decay')
    plt.xlabel('Episode')
    plt.ylabel('Epsilon')
    
    plt.tight_layout()
    plt.savefig('training_progress.png')
    plt.show()
    
    return agent

if __name__ == "__main__":
    print("Starting training...")
    agent = train_agent(episodes=500, render_interval=50)
    print("Training complete!")