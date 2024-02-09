import matplotlib.pyplot as plt
import seaborn as sns

def visualize_data(df, x, y, x_label, y_label, title, file_name):
    # Set a style for seaborn
    sns.set_style("whitegrid")

    plt.figure(figsize=(10, 6))
    sns.scatterplot(x=x_label, y='is_active', data=df)
    plt.plot(x, y, color='red')  # Overlaying the regression line
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.show()
