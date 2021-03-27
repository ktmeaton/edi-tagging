#!/usr/bin/env python3

# Import the necessary mocules
from typing import Dict
import click # Command-line interace
import pandas as pd # Dataframe manipulation
import os # Search through files
import copy

import networkx as nx

from bokeh.models import (BoxZoomTool, Circle, HoverTool,
                           MultiLine, Plot, Range1d, ResetTool,)
from bokeh.plotting import from_networkx
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.palettes import Category10

# functions
def count_elements(d):
    if isinstance(d, dict):
        return sum([1 + count_elements(_x) for _x in d.values()])
    else: 
        return 1

# Command-line arguments
@click.command()
@click.help_option("--help", "-h")
@click.option(
    "--keywords",
    help="Keywords tab-delimited file.",
    type=click.Path(exists=True, dir_okay=False, allow_dash=True),
)
@click.option(
    "--pdf-dir",
    help="Directory of course syllabi pdfs.",
    type=click.Path(exists=True, dir_okay=True, allow_dash=True),
)
# The main function
def main(
    keywords: str,
    pdf_dir: str,
):
    """Automated EDI Tagging of Course Syllabi"""
    keywords_path = keywords
    keywords_df = pd.read_csv(keywords_path, sep='\t')

    # Store the mapping of concept to keyword in a dictionary
    concept_dict = {}
    # Store the syllabi data in a separate dict
    data_dict = {}

    # Parse the keywords file into a dictionary
    for concept in keywords_df["Concept"]:
        # Store the concept in the dictionary
        if concept not in concept_dict:
            concept_dict[concept] = {}

        # Store the keywords associated with a concept
        concept_df = keywords_df[keywords_df["Concept"] == concept]
        keywords = concept_df["Keywords"].values[0]
        # Keywords should be a comma-separated list
        keywords_list = keywords.split(",")
        # Add the keywords to the dictionary along with word counters
        concept_dict[concept] = {k : 0 for k in keywords_list}

    # Iterate through the pdfs directory
    for file in os.listdir(pdf_dir):
        # Store the relative path to the file
        file_path = os.path.join(pdf_dir, file)
        # Identify the file extension
        ext = os.path.splitext(file)[1]
        file_name = os.path.splitext(file)[0]
        year = file_name.split("_")[0]
        term = file_name.split("_")[1]
        department = file_name.split("_")[2]
        course = file_name.split("_")[3]

        # If it's a text file
        if ext == ".txt":
            txt_file = open(file_path, "rt")
            file_content = txt_file.read().strip().lower()

        # If it's a pdf file
        elif ext == ".pdf":
            continue

        # Add course to dict
        data_dict[course] = {}

        for concept in concept_dict:
            # Add concept to course
            data_dict[course][concept] = {}
            
            for keyword in concept_dict[concept]:
                # Count occurrence of the keyword
                keyword_count = file_content.count(keyword)
                # If not 0, Add the count to the concept dictionary
                if keyword_count > 0:
                    # Increment counters
                    data_dict[course][concept][keyword] = keyword_count

            # If no keywords were found, remove this concept from the data
            if len(data_dict[course][concept]) == 0:
                data_dict[course].pop(concept)

    #-----------------------------------------------
    # Create network graph

    # Start with an empty undirected graph
    G = nx.Graph()

    # Or add 1 level dict
    #G = nx.Graph(data_dict)

    for course in data_dict.keys():
        for concept in data_dict[course].keys():
            for keyword in data_dict[course][concept].keys():
                G.add_edge(course, concept)
                G.add_edge(concept, keyword)

 
    # Use the boken accessory function
    gr = from_networkx(G, nx.spring_layout, scale=1, center=(0, 0))
    #gr = from_networkx(G, nx.shell_layout, center=(0, 0))
    # Check data
    # print(gr.node_renderer.data_source.data)

    # Style nodes
    node_attr = {}
    base_size = 10

    keyword_color = Category10[4][0]
    concept_color = Category10[4][1]
    course_color = Category10[4][2]

    # Initialize default values for nodes
    node_attr["size"] = {node_name: base_size for node_name in G.nodes}
    node_attr["color"] = {node_name: keyword_color for node_name in G.nodes}
    node_attr["concept_num"] = {node_name: 0 for node_name in G.nodes}
    node_attr["kw_num"] = {node_name: 0 for node_name in G.nodes}

    for node in G.nodes:
        # Check if it's a course
        if node in data_dict:
            node_attr["color"][node] = course_color
            node_attr["size"][node] = len(data_dict[node]) * base_size
            node_attr["concept_num"][node] = len(data_dict[node])
            node_attr["kw_num"][node] = count_elements(data_dict[node])
        # Check if it's a concept
        else:
            for course in data_dict:
                for concept in data_dict[course]:
                    if node == concept:
                        node_attr["size"][node] = len(data_dict[course][node]) * base_size
                        node_attr["color"][node] = concept_color
                        node_attr["concept_num"][node] = 1                        
                        node_attr["kw_num"][node] = count_elements(data_dict[course][node])
                        break

    # gr.node_renderer.data_source.data is a dictionary
    gr.node_renderer.data_source.data['size'] = list(node_attr["size"].values())
    gr.node_renderer.data_source.data['color'] = list(node_attr["color"].values())
    gr.node_renderer.data_source.data['concept_num'] = list(node_attr["concept_num"].values())
    gr.node_renderer.data_source.data['kw_num'] = list(node_attr["kw_num"].values())    

    gr.node_renderer.glyph = Circle(
        size='size',
        fill_color='color',
    )         

    #-----------------------------------------------
    # Plotting    

    # Plot setup
    plot = Plot(plot_width=600, plot_height=400)
    plot.title.text = "EDI Tagging | Department of History | Fall 2020"
    node_hover_tool = HoverTool(tooltips=[
        ("Name", "@index"), 
        ("Concepts", "@concept_num"),
        ("Keywords", "@kw_num")
        ])
    plot.add_tools(node_hover_tool, BoxZoomTool(), ResetTool())


    # Add the graph to the plot
    plot.renderers.append(gr)

    # Save to file
    html = file_html(plot, CDN, "tmp.html")
    with open("edi-tagging-graph.html", "w") as outfile:
        outfile.write(html)    


if __name__ == "__main__":
    main()
