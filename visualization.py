"""Visualization module for generating charts as base64 images."""
import base64
import io
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class QuizVisualizer:
    """Generator for quiz visualizations as base64-encoded images."""
    
    @staticmethod
    def figure_to_base64(fig: plt.Figure) -> str:
        """Convert a matplotlib figure to base64 string."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        return img_base64
    
    @staticmethod
    def create_bar_chart(data: Dict[str, float], title: str = "", 
                        xlabel: str = "", ylabel: str = "") -> str:
        """Create a bar chart from dictionary data."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        keys = list(data.keys())
        values = list(data.values())
        
        bars = ax.bar(keys, values)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_line_chart(x_data: List, y_data: List, title: str = "",
                         xlabel: str = "", ylabel: str = "") -> str:
        """Create a line chart from x and y data."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(x_data, y_data, marker='o')
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_pie_chart(data: Dict[str, float], title: str = "") -> str:
        """Create a pie chart from dictionary data."""
        fig, ax = plt.subplots(figsize=(8, 8))
        
        labels = list(data.keys())
        sizes = list(data.values())
        
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title(title)
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_scatter_plot(x_data: List, y_data: List, title: str = "",
                           xlabel: str = "", ylabel: str = "") -> str:
        """Create a scatter plot."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.scatter(x_data, y_data, alpha=0.6)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_histogram(data: List[float], bins: int = 20, title: str = "",
                        xlabel: str = "", ylabel: str = "Frequency") -> str:
        """Create a histogram."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(data, bins=bins, edgecolor='black', alpha=0.7)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_dataframe_chart(df: pd.DataFrame, chart_type: str = "bar",
                              x_col: Optional[str] = None,
                              y_col: Optional[str] = None,
                              title: str = "") -> str:
        """Create a chart from a pandas DataFrame."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "bar":
            if x_col and y_col:
                df.plot(kind='bar', x=x_col, y=y_col, ax=ax, title=title)
            else:
                df.plot(kind='bar', ax=ax, title=title)
        elif chart_type == "line":
            if x_col and y_col:
                df.plot(kind='line', x=x_col, y=y_col, ax=ax, title=title, marker='o')
            else:
                df.plot(kind='line', ax=ax, title=title, marker='o')
        elif chart_type == "hist":
            if y_col:
                df[y_col].hist(bins=20, ax=ax, edgecolor='black', alpha=0.7)
            else:
                df.hist(bins=20, ax=ax, edgecolor='black', alpha=0.7)
            ax.set_title(title)
        elif chart_type == "scatter":
            if x_col and y_col:
                df.plot(kind='scatter', x=x_col, y=y_col, ax=ax, title=title, alpha=0.6)
        
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
    
    @staticmethod
    def create_table_image(data: List[Dict[str, Any]], title: str = "") -> str:
        """Create an image of a table."""
        if not data:
            # Create empty table
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.text(0.5, 0.5, "No data", ha='center', va='center', fontsize=14)
            ax.set_title(title)
            ax.axis('off')
            plt.tight_layout()
            return QuizVisualizer.figure_to_base64(fig)
        
        df = pd.DataFrame(data)
        
        fig, ax = plt.subplots(figsize=(12, min(8, len(df) * 0.5 + 2)))
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(cellText=df.values, colLabels=df.columns,
                        cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        
        # Style header
        for i in range(len(df.columns)):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax.set_title(title, pad=20, fontsize=14, weight='bold')
        
        plt.tight_layout()
        return QuizVisualizer.figure_to_base64(fig)
