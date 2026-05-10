import matplotlib.pyplot as plt
import numpy as np

# Data from your evaluation results
categories = ['Easy', 'Medium', 'Hard']
accuracy = [100.00, 86.67, 66.67]
precision = [100.00, 96.31, 89.77]
recall = [100.00, 96.67, 89.55]

x = np.arange(len(categories))
width = 0.25  # the width of the bars

# Create the figure and axes
fig, ax = plt.subplots(figsize=(10, 6))

# Plotting the three metric bars
rects1 = ax.bar(x - width, accuracy, width, label='Accuracy (Exact Match)', color='#2c3e50')
rects2 = ax.bar(x, precision, width, label='Character Precision', color='#2980b9')
rects3 = ax.bar(x + width, recall, width, label='Character Recall', color='#3498db')

# Add titles and formatting
ax.set_ylabel('Percentage (%)', fontsize=12)
ax.set_title('ALPR Performance Metrics by Category', fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.legend(loc='lower left', frameon=True, fontsize=10)
ax.set_ylim(0, 115) # Leave space for labels
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Function to add data labels on top of bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)

plt.tight_layout()
plt.savefig('alpr_performance_metrics.png', dpi=300)
plt.show()