# -*- coding: utf-8 -*-
"""
Contains functions to help build the GUI interface.
"""

from tkinter import ttk
import tkinter as tk

#==============================================================================
#================================= Make Input =================================
#==============================================================================

def make_input(frame, text, var, input_type, row, column, padx = 5, pady = 5,
               command = None, sticky = ['NSEW', None], width = None,
               options = None, vals = [0, 10], increment = 1, rowspan = None, 
               columnspan = None, label_font = ('Verdana', 8)):

    '''
    Function to build GUI inputs consisting of a label and an input.

    **Parameters:**

    frame : tk.Frame or tk.LabelFrame
        Container in which to place the object

    text : str
        Text to display in the label

    var : tk variable
        Variable to assosiate with the input

    input_type : str
        Type of input to use. Must be one of Entry, Spinbox, OptionMenu, 
        Checkbutton or Label

    row : int
        Row number, will be the same for label and input

    column : int
        Column number, the input will be column + 1

    padx : int (optional)
        X-padding to apply to the label and input. Default is 5

    pady : int (optional)
        Y-padding to apply to the label and input. Default is 5

    command : func
        function to run on change to the input value

    sticky : str or tuple of strings (optional)
        Direction to stick the object (compass direction). If given as a tuple 
        the first corresponds to the label and the second to the entry. Default 
        is None

    width : float (optional)
        Width of the entry. Default is None.

    options : list (optional)
        List of options for an Option Menu. Default is None

    vals : tuple or list (optional)
        Sets the range of values for a spinbox. If two values are give it sets 
        the limits (from, to)

    increment : int (optional)
        Value spacing for a spinbox. Default is 1

    rowspan : int (optional)
        Number of rows the entry will span. Default is None

    columnspan : int (optional)
        Number of columns the entry will span. Default is None

    label_font : tuple (optional)
        Font tuple in the form (font, size) for the label. Default is 
        ('Verdana', 8)

    **Returns:**
        
    label : tk.Label object
        Input label object

    entry : tk object
        Input entry object, type depends on the input_type
    '''

    # Unpack stickyness
    if sticky == None:
        label_sticky = None
        entry_sticky = None
    elif len(sticky) == 2:
        label_sticky = sticky[0]
        entry_sticky = sticky[1]
    else:
        label_sticky = sticky
        entry_sticky = sticky

    # Create the input label
    label = ttk.Label(frame, text = text, font = label_font)
    label.grid(row=row, column=column, padx=padx, pady=pady,
               sticky=label_sticky)

    # Check that the entry type is valid
    if input_type not in ['Entry', 'Spinbox', 'OptionMenu', 'Label', 
                          'Checkbutton']:
        raise TypeError('Data entry type "' + input_type + '" not recognised')


    # Normal entry
    if input_type == 'Entry':
        if command == None:
            validate = None
        else:
            validate = "focusout"
        entry = ttk.Entry(frame, textvariable = var, width = width, 
                          validate = validate, validatecommand = command)


    # Spinbox
    if input_type == 'Spinbox':

        # Check if range is from:to or a list
        if len(vals) == 2:
            entry = tk.Spinbox(frame,
                               textvariable = var, 
                               width = width, 
                               from_ = vals[0],
                               to = vals[1], 
                               command = command, 
                               increment = increment)

        else:
            entry = tk.Spinbox(frame, 
                               textvariable = var, 
                               width = width, 
                               values = vals,
                               command = command, 
                               increment = increment)

        # Set first value
        #entry.update(var.get())


    # Option Menu
    if input_type == 'OptionMenu':
        entry = ttk.OptionMenu(frame, var, *options, command = command)
        entry.config(width = width)


    # Label
    if input_type == 'Label':
        entry = ttk.Label(frame, textvariable = var)


    # Checkbutton
    if input_type == 'Checkbutton':
        entry = ttk.Checkbutton(frame, variable = var)


    # Add entry to the frame
    entry.grid(row=row, column=column+1, padx=padx, pady=pady, 
               sticky=entry_sticky, rowspan=rowspan, columnspan=columnspan)

    return label, entry

#==============================================================================
#================================ Update Graph ================================
#==============================================================================

def update_graph(lines, axes, canvas, new_data):

    '''
    Function to update a matplotlib figure

    **Parameters:**
        
    lines : list
        The plots to update

    axes : list
        Axes that correspond to the lines (must be same length and order as 
        lines)

    canvas : tkagg canvas object
        Canvas that holds the axes

    new_data : array
        New data to plot. Has the form [[x1, y1, x1lims, y1lims],
                                        [x2, y2, x2lims, y2lims],...]
        
    **Returns:**
        
    None
    '''

    # Unpack new data
    if len(new_data.shape) > 1:
        xdata = new_data[:,0]
        ydata = new_data[:,1]
        xlims = new_data[:,2]
        ylims = new_data[:,3]

    else:
        xdata = [new_data[0]]
        ydata = [new_data[1]]
        xlims = [new_data[2]]
        ylims = [new_data[3]]

    # Iterate plotting over each data series
    for i in range(len(lines)):

        # Update data points on the graph
        lines[i].set_xdata(xdata[i])
        lines[i].set_ydata(ydata[i])

        # Rescale the axes
        axes[i].relim()
        axes[i].autoscale_view()

        try:
            # If auto, pad by 10% of range
            if xlims[i] == 'auto':
                x_min = min(xdata[i]) - abs(max(xdata[i]) - min(xdata[i]))*0.1
                x_max = max(xdata[i]) + abs(max(xdata[i]) - min(xdata[i]))*0.1
                axes[i].set_xlim(x_min, x_max)

            # If false set as limits +/- 1
            elif xlims[i] == False:
                axes[i].set_xlim(min(xdata[i])-1, max(xdata[i])+1)

            # If fixed, fix value
            else:
                axes[i].set_xlim(xlims[i][0], xlims[i][1])

            # Do same for y axis
            if ylims[i] == 'auto':
                y_min = min(ydata[i]) - abs(max(ydata[i]) - min(ydata[i]))*0.1
                y_max = max(ydata[i]) + abs(max(ydata[i]) - min(ydata[i]))*0.1
                axes[i].set_ylim(y_min, y_max)

            elif ylims[i] == False:
                axes[i].set_ylim(min(ydata[i])-1, max(ydata[i])+1)

            else:
                axes[i].set_ylim(ylims[i][0], ylims[i][1])

        except ValueError:
            pass

    # Apply changes
    canvas.draw()