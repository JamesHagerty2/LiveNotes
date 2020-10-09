from cmu_112_graphics import *
from tkinter.filedialog import askopenfilename
import random
import csv
import speech_recognition as sr
import requests
from bs4 import BeautifulSoup
import urllib
import pickle
import string

# LiveNotes app with every feature and mode

# graphics package from:
# https://www.cs.cmu.edu/~112/notes/notes-animations-part1.html

# modal app console adapted from:
# https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html

# various graphics colors from:
# http://www.science.smith.edu/dftwiki/index.php/Color_Charts_for_TKinter

# disabled width and height resizing in the graphics package
class HelpMode(Mode):
    def appStarted(mode):
        # image uploading and editing techniques from:
        # https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html
        # images comprising tutorial
        mode.Tutorial1 = mode.loadImage('Tutorial1.jpg')
        mode.Tutorial1 = mode.scaleImage(mode.Tutorial1, 1/2.85)
        mode.Tutorial2 = mode.loadImage('Tutorial2.jpg')
        mode.Tutorial2 = mode.scaleImage(mode.Tutorial2, 1/2.85)
        mode.Tutorial3 = mode.loadImage('Tutorial3.jpg')
        mode.Tutorial3 = mode.scaleImage(mode.Tutorial3, 1/2.85)
        mode.Tutorial4 = mode.loadImage('Tutorial4.jpg')
        mode.Tutorial4 = mode.scaleImage(mode.Tutorial4, 1/2.85)

    # draws tutorial images in the right place
    def redrawAll(mode, canvas):
        canvas.create_text(mode.width/2-300, mode.height*7/8, 
                           text='Click anywhere to return to the home screen.',
                           font='Arial 18 bold', fill='RoyalBlue3')
        canvas.create_image(185, mode.height/2-150,
                            image=ImageTk.PhotoImage(mode.Tutorial1))
        canvas.create_image(mode.width/2, mode.height/2-110,
                            image=ImageTk.PhotoImage(mode.Tutorial4))
        canvas.create_image(1010, mode.height/2-175,
                            image=ImageTk.PhotoImage(mode.Tutorial3))
        canvas.create_image(1010, mode.height/2+165,
                            image=ImageTk.PhotoImage(mode.Tutorial2))

    # return to the home screen       
    def mousePressed(mode, event):
        mode.app.setActiveMode(mode.app.splashScreenMode)

# home screen
class SplashScreenMode(Mode):
    def redrawAll(mode, canvas):
        canvas.create_text(mode.width/2, mode.height/2-30,
                          text='Welcome to LiveNotes!', font='Arial 36 bold')
        canvas.create_text(mode.width/2, mode.height/2 + 140,
                          text='Press n or click to start.', 
                          font='Arial 26 bold')
        canvas.create_text(mode.width/2, mode.height/2+10,
                          text='a 15-112 Term Project by James Hagerty', 
                          font='Arial 18 bold', fill='RoyalBlue3')
        canvas.create_text(mode.width*7/8, mode.height-60,
                           text='Open Help Menu', font='Arial 14 bold')
    # starts LiveNotes
    def keyPressed(mode, event):
        if event.key == 'n':
            mode.app.setActiveMode(mode.app.noteBookMode)
    # either start LiveNotes or go to the help screen
    def mousePressed(mode, event):
        if event.x > mode.width*7/8-60 and event.y > mode.height-60-20:
            mode.app.setActiveMode(mode.app.helpMode)
        else:
            mode.app.setActiveMode(mode.app.noteBookMode)       

# erases former text image representation and replaces it with current text
# image representation
def textTransition(page, images):
    for imageData in images:
        page = cleanAllImageText(imageData, page)
    for imageData in images:
        page = imageOnText(imageData, page)
    return page

# returns list indicating the images below
def imagesBelow(imageTagsBelow, images):
    shiftDownIndexes = []
    for tag in imageTagsBelow:
        for img in images:
            if tag in img:
                shiftDownIndexes.append(images.index(img))
    return shiftDownIndexes

# iterates over a copied text block and a page to see if there is space to
# paste that text block
def isLegalPaste(row, col, text, page):
    if text == [] or row==None or col==None:
        return
    # check if copied text will bump into text in the row it is being pasted
    blankColSpace = 0
    for c in range(col, 56):
        if page[row][c] == None: 
            blankColSpace += 1
        elif (page[row][c][0] == ' ' and not 'image' in page[row][c] and 
              not 'table' in page[row][c]):
            blankColSpace += 1 
        else:
            break
    if blankColSpace < len(text[0]):
        return False
    # check if there are enough rows to fit the height of the copied text block
    blankRowsBelow = 0
    for r in range(row, 21):
        if page[r] == [None]*56:
            blankRowsBelow += 1
    if blankRowsBelow < len(text):
        return False
    return True

# trims blank edges off of a copy/cut/paste selected text block and returns the
# edited text block
def trimTextBlock(textBlock):
    blankRows = []
    # remove blank rows
    r = 0
    for row in textBlock:
        if row == [None]*len(row):
            blankRows.append(r)
        r += 1
    # pop blank rows in a backwards order to avoid popping non blank rows
    for rowPop in blankRows[::-1]:
        textBlock.pop(rowPop)
    if textBlock == []:
        return textBlock
    # remove blank cols on the edges but not those in between text
    # remove blank cols from left end
    blankCols = []
    for col in range(len(textBlock[0])):
        allNone = True
        # breaks iteration if the the left edge has been cleared
        if col != 0 and col-1 not in blankCols:
            allNone = False
            break
        for row in textBlock:
            if row[col] != None:
                allNone = False
        if allNone:
            blankCols.append(col)
    # remove blank cols from right end
    colEnd = len(textBlock[0])-1
    for col in range(colEnd, -1, -1):
        allNone = True
        # breaks iteration if the right end has been cleared
        if col != colEnd and col+1 not in blankCols:
            allNone = False
            break
        for row in textBlock:
            if row[col] != None:
                allNone = False
        if allNone:
            blankCols.append(col)
    # pop blank cols in a backwards order to avoid popping non blank cols
    blankCols = sorted(blankCols)
    blankCols = blankCols[::-1]
    for colPop in blankCols:
        for row in range(len(textBlock)):
            textBlock[row].pop(colPop)
    return textBlock
            
# determines the closest, next column to the cursor that is not filled by an
# image (for text wrapping)
def colTextWrap(page, row, col):
    for i in range(col, 56):
        if (page[row][i] == None):
            return i
        elif not 'image' in page[row][i]:
            return i
    return col-1

# determines whether an image can be placed in a spot by checking if the 2D list
# page is empty within the corners of the image
def legalImagePlacement(imageData, page):
    # image corners
    topLeft = imageData[0]
    bottomRight = imageData[1]
    for row in range(topLeft[0], bottomRight[0]):
        if row > 20:
            return False
        for col in range(topLeft[1], bottomRight[1]):
            if col > 55:
                return False
            if page[row][col] == None:
                continue
            elif (page[row][col][0] != ' ' or 'image' in page[row][col] or
                  'table' in page[row][col]):
                return False
    return True

# determines if resizing or dragging the image makes it bump into other text
# or images
def legalImageMovement(imageData, page):
    # imageTag is the name of the strings representing the image on the 2D list
    # of text
    imageTag = imageData[3]
    topLeft = imageData[0]
    bottomRight = imageData[1]
    for row in range(topLeft[0], bottomRight[0]):
        if row > 20:
            return False
        for col in range(topLeft[1], bottomRight[1]):
            if col > 55:
                return False
            if page[row][col] == None:
                continue
            if page[row][col] == imageTag:
                continue
            elif (page[row][col][0] != ' ' or 'image' in page[row][col] or
                  'table' in page[row][col]):
                return False
    return True

# efficient way of removing all string representations of an image on the 2D
# list of text when the strings are to be moved and returns edited list
# only used when only one image is being altered
def cleanImageText(imageData, page):
    topLeft = imageData[0]
    bottomRight = imageData[1]
    imageTag = imageData[3]
    # only spans the 2D list area where the image used to be
    for row in range(topLeft[0], bottomRight[0]):
        for col in range(topLeft[1], bottomRight[1]):
            if page[row][col] == imageTag:
                page[row][col] = None
    return page

# removes all strings representing an image on the 2D list of text and returns
# edited list
# used for more complex image movement operations where more text than just the
# image of focus is being changed/moved
def cleanAllImageText(imageData, page):
    imageTag = imageData[3]
    for row in range(21):
        for col in range(56):
            if page[row][col] == imageTag:
                page[row][col] = None
    return page

# modifies the 2D list of text to represent the space of an image by its
# serial number
def imageOnText(imageData, page):
    topLeft = imageData[0]
    bottomRight = imageData[1]
    imageTag = imageData[3]
    # places an image within its corners on the 2D list
    for row in range(topLeft[0], bottomRight[0]):
        for col in range(topLeft[1], bottomRight[1]):
            page[row][col] = imageTag
    return page

# determines/returns the index of an image in the list containing images and 
# what action is to be performed on the image (moving or resizing) depending on
# what section of the image was clicked
def getImageData(whichImage, images, row, col):
    imageIndex = None
    imageAction = None
    for data in images:
        if data[3] == whichImage:
            imageIndex = images.index(data)
            break
    # checks if the bottom right fourth of the image was clicked, this means
    # the image is to be resized
    if ((row > (images[imageIndex][0][0]+images[imageIndex][1][0])/2) and
        (col > (images[imageIndex][0][1]+images[imageIndex][1][1])/2)):
        imageAction = 'resizing'
    # clicking on the image elsewhere means preparing to move it
    else:
        imageAction = 'moving'
    return (imageIndex, imageAction)

# used when bulleting/numbering lists to prevent a row with an image from
# being bulleted, determines if an image takes up part of the row
def imageInRow(page, row):
    for char in page[row]:
        if char == None:
            continue
        elif 'image' in char:
            return True
    return False

# creates and returns the multidimensional list representing a table
def makeTable(rows, cols, rowPlaced, serialNum):
    table = []
    corner = [rowPlaced, 0]
    for i in range(rows):
        tableRow = []
        leftSide = corner[:]
        leftSide[0] = i+corner[0]
        tableRow.append(leftSide)
        for j in range(cols):
            tableRow.append([])
        rightSide = leftSide[:]
        rightSide[0] += 1
        rightSide[1] = corner[1] + 55
        tableRow.append(rightSide)
        table.append(tableRow)
    # serial number for the table's text representation
    tableData = [table, ' ■table'+str(serialNum)]
    return tableData

# checks if a table placement or movement is legal
def legalTable(page, table):
    if table[0] == []:
        return
    topRow = table[0][0][0][0]
    bottomRow = table[0][-1][-1][0]
    if bottomRow >= 22:
        return False
    for row in range(topRow, bottomRow):
        if page[row] != [None]*56:
            return False
    return True

# creates 2D list text representation of a table
def tableOnText(page, table):
    if table[0]==[] or None in table:
        return page
    topLeft = table[0][0][0]
    bottomRight = table[0][-1][-1]
    tableTag = table[1]
    for row in range(topLeft[0], bottomRight[0]):
        for col in range(topLeft[1], bottomRight[1]+1):
            page[row][col] = tableTag
    return page

# cleans 2D list text representation of a table for when it changes
def cleanTable(page, tableTag):
    for row in range(21):
        for col in range(56):
            if page[row][col] == tableTag:
                page[row][col] = None
    return page

# determines and returns the index of the table that was clicked
def whichTable(tables, tableTag):
    for table in tables:
        if table[1] == tableTag:
            return tables.index(table)

# determines and returns which cell of a table is currently being typed in,
# represented by the row and column of the table structure
def whichCell(table, row, col):
    tableRow = None
    tableCol = None
    for r in range(len(table)):
        if row >= table[r][0][0] and row <= table[r][-1][0]:
            tableRow = r
    colsPerRow = len(table[0])-2
    # add one to tableCol because the first element of every row is a coordinate 
    # list, not a cell string
    tableCol = int(col//(56/colsPerRow)+1)
    return [tableRow, tableCol]

# updates the location of cell rows in a table when one cell expands
def stretchTable(table, onRow):
    table[onRow][-1][0] += 1
    for row in range(onRow+1, len(table)):
        table[row][0][0] += 1
        table[row][-1][0] += 1
    return table

# edits and returns table based on input (adding or deleting rows and columns)
def editTable(page, table, choice, tRow, tCol, fullTable, row, images, tables):
    if table==[]: return
    # inserts a row at a clicked on location
    tRowC=row
    newRow=[[tRowC,0]]+[[] for i in range(len(table[0])-2)]+[[tRowC+1, 55]]
    if choice == 'InsertRow':
        table.insert(tRow, newRow)
        # adjust coordinates for other rows below insertion
        for row in range(tRow+1, len(table)):
            table[row][0][0] += 1
            table[row][-1][0] += 1
    # deletes a row at a clicked on location
    if choice == 'DeleteRow':
        if table==[]:
            return
        # adjust coordinates for other rows below deleted row
        # prevent an illegal row deletion (e.g. deleting row 2 when there are
        # not even 2 rows)
        if tRow >= len(table):
            return
        delRowHeight = table[tRow][-1][0]-table[tRow][0][0]
        rowOnTable = int(table[tRow][0][0])
        for row in range(tRow+1, len(table)):
            table[row][0][0] -= delRowHeight
            table[row][-1][0] -= delRowHeight
        # ensures only rows at the chosen index are popped
        if tRow < len(table): table.pop(tRow)             
    # insert a column at a clicked on location, limit of 16 columns
    if choice == 'InsertCol' and len(table[0]) < 16:
        for row in range(len(table)):
            table[row].insert(tCol, [])
    if choice == 'DeleteCol' and not table[0][tCol]==table[0][-1]:
        for row in range(len(table)):
            table[row].pop(tCol)
    # undoes a row insertion if it is illegal by recursively deleting it
    fullTable[0] = table
    if not legalTable(page, fullTable):
        if fullTable[0]==[]: return
        lowestBlank = lowestBlankRow(page)
        insertRow = table[-1][-1][0]-1
        # moves down the rest of the text under the table as a row is inserted
        if insertRow < lowestBlank:
            page.pop(lowestBlank)
            page.insert(insertRow, [None]*56)
            moveImagesDown(page, images, insertRow, lowestBlank, False, tables)
            resetImagesTables(page, images, tables)
            return
        # recursively delete an illegal row insertion
        return editTable(page, table,'DeleteRow', tRow, tCol, fullTable, row,
                        images, tables)
    return table
    
# checks which tables are below
def tablesBelow(tableTagsBelow, tables):
    shiftDownIndexes = []
    for tag in tableTagsBelow:
        for table in tables:
            if tag in table:
                shiftDownIndexes.append(tables.index(table))
    return shiftDownIndexes

# cleans former text representations of tables and images and recreates them
# according to their updated positions
def resetImagesTables(page, images, tables):
    for imageData in images:
        page = cleanAllImageText(imageData, page)
        page = imageOnText(imageData, page)
    for tableData in tables:
        page = cleanTable(page, tableData[1])
        page = tableOnText(page, tableData)

# moves tables and images up for actions like deleting upwards or moving
# an image up against text to move it up
def moveImagesUp(page, images, highestBlank, row, exception, tables):
    # moves images up
    imageTagsAbove = set()
    for imageInfo in images:
        if images==[]: break
        # exception for deleting to avoid text spacing error
        if exception and row <= imageInfo[1][0]:
            imageTagsAbove.add(imageInfo[3])
        # limits to images that can only be moved up legally
        elif row >= imageInfo[1][0] and not imageInfo[1][0] < highestBlank:
            imageTagsAbove.add(imageInfo[3])
    shiftUpIndexes = []
    for tag in imageTagsAbove:
        if images==[]: break
        for img in images:
            if tag in img:
                shiftUpIndexes.append(images.index(img))
    for image in shiftUpIndexes:
        if images==[]: break
        imageData = images[image]
        highestBlank = highestBlankRow(page)
        if imageData[1][0] > highestBlank and not imageData[0][0] == 0: 
            imageData[0][0] -= 1
            imageData[1][0] -= 1
    # moves tables up
    tableTagsAbove = set()
    for tableInfo in tables:
        if tableInfo[0]==[]: break
        # avoids text shifting error
        if exception and row <= tableInfo[0][-1][-1][0]:
            tableTagsAbove.add(tableInfo[1])
        # limits to tables that can be moved up legally
        elif (row >= tableInfo[0][-1][-1][0] and 
              not tableInfo[0][-1][-1][0] < highestBlank):
            tableTagsAbove.add(tableInfo[1])
    shiftUpIndexes = []
    for tag in tableTagsAbove:
        for table in tables:
            if tag in table:
                shiftUpIndexes.append(tables.index(table))
    for table in shiftUpIndexes:
        tableData = tables[table]
        highestBlank = highestBlankRow(page)
        if (tableData[0][-1][-1][0] > highestBlank and 
            not tableData[0][0][0][0] == 0): 
            for row in range(len(tableData[0])):
                 tableData[0][row][0][0] -= 1
                 tableData[0][row][-1][0] -= 1
    return

# moves images and tables down for actions like entering or new text pushing
# downwards or other images being pushed down
def moveImagesDown(page, images, row, lowestBlank, exception, tables):
    # moves images down
    imageTagsBelow = set()
    for imageInfo in images:
        # limits to images below the object/action moving them down
        if row <= imageInfo[0][0]:
            imageTagsBelow.add(imageInfo[3])
    shiftDownIndexes = imagesBelow(imageTagsBelow, images)
    for image in shiftDownIndexes:
        imageData = images[image]
        page = cleanAllImageText(imageData, page)
        if imageData[1][0]-1 < lowestBlank: 
            imageData[0][0] += 1
            imageData[1][0] += 1
        elif exception == True:
            imageData[0][0] += 1
            imageData[1][0] += 1
    # moves tables down
    tableTagsBelow = set()
    for tableInfo in tables:
        # limits to tabels below the object/action moving them down
        if row <= tableInfo[0][0][0][0]:
            tableTagsBelow.add(tableInfo[1])
    shiftDownIndexes = tablesBelow(tableTagsBelow, tables)
    for table in shiftDownIndexes:
        tableData = tables[table]
        page = cleanTable(page, tableData[1])
        if tableData[0][-1][-1][0]-1 < lowestBlank:
            for row in range(len(tableData[0])):
                 tableData[0][row][0][0] += 1
                 tableData[0][row][-1][0] += 1
    # clean former text representations off before creating new ones
    resetImagesTables(page, images, tables)
    return

# determines and returns the index of the lowest blank row on the page
def lowestBlankRow(page):
    lowestBlank = None
    while lowestBlank == None:
        for tryRow in range(20, -1, -1):
            if page[tryRow] == [None]*56:
                lowestBlank = tryRow
                break
        break
    # prevents Nonetype crashes if there is not a lowest blank row
    if lowestBlank==None: return 0
    return lowestBlank

# determines the highest blank row on a page     
def highestBlankRow(page):
    highestBlank = None
    while highestBlank == None:
        for tryRow in range(0, 21):
            if page[tryRow] == [None]*56:
                highestBlank = tryRow
                break
        break
    # prevents NoneType crashes if there is no highest blank
    if highestBlank==None: return 20
    return highestBlank

# makes sure eraser only erases drawings in its circle
def inEraserBounds(tupX, tupY, eraser, radius):
    if eraser == (None, None) or (tupX, tupY) == (None, None):
        return
    (x, y) = eraser
    radius *= 1.25
    return (x-radius < tupX < x+radius) and (y-radius < tupY < y+radius)

# shortens the list of drawing coordinates by getting rid of erased (four None)
# tuples and then returns the edited tuples list
def cleanTuples(tuples):
    removeIndices = []
    for i in range(len(tuples)-2):
        # it is arbitrary to have two tuples of four Nones in a row
        if ((tuples[i] == (None, None, None, None)) and
           (tuples[i+1] == (None, None, None, None))):
           removeIndices.append(i)
    for j in removeIndices[::-1]:
        tuples.pop(j)
    return tuples

# file writing technique adapted from:                 
# https://www.youtube.com/watch?v=s1XiCh-mGCA
# saves all of the notebook data into a file that can be reopened later
def saveFile(nameFile, typedText, drawingTuples, speechNotes, pageImages,
             pageTables):
    if nameFile == None:
        return
    with open(nameFile+'.csv', 'w', newline='') as file:
        fileMaker = csv.writer(file)
        for page in typedText:
            fileMaker.writerow(['START'])
            for line in page:
                lineCopy = line[:]
                # prevents typed commas from being deleted when the file
                # is opened later and its lines are .split(',')
                for i in range(len(lineCopy)):
                    if lineCopy[i] == ',':
                        lineCopy[i] = 'COMMA'
                fileMaker.writerow(lineCopy)
            fileMaker.writerow(['END'])
        for drawing in drawingTuples:
            fileMaker.writerow(['START2'])
            for tup in drawing:
                fileMaker.writerow(tup)
            fileMaker.writerow(['END2'])
        for speechPage in speechNotes:
            fileMaker.writerow(['START3'])
            fileMaker.writerow(speechPage)
            fileMaker.writerow(['END3'])
        for images in pageImages:
            fileMaker.writerow(['START4'])
            for image in images:
                fileMaker.writerow(image)
            fileMaker.writerow(['END4'])
        for tables in pageTables:
            fileMaker.writerow(['START5'])
            for table in tables:
                fileMaker.writerow(table)
            fileMaker.writerow(['END5'])
    return

# reads CSV files tailored for and created in the app and opens them, returns
# all data structures from the saved file
def openFile(filename):
    with open(filename, "rt") as f:
        pages = f.read()
    pages = pages.split('\n')
    allPages = []
    page = []
    pageLine = []
    tuplesStart = None
    # recreates text data from saved file
    for line in pages:
        if line == 'START2':
            # determines where to start recreating drawings
            tuplesStart = pages.index(line)
            break
        if line == 'START':
            continue
        elif line == 'END':
            allPages.append(page)
            page = []
        else:
            for char in line.split(','):
                if char == '':
                    pageLine.append(None)
                # ensures that text commas will not be deleted later when the
                # line is read with .split(',') when opening the file
                elif char == 'COMMA':
                    pageLine.append(',')
                else:
                    pageLine.append(char)
            page.append(pageLine)
            pageLine = []
    # recreates drawings data from saved file
    allPagesDraw = []
    pageDraw = []
    pageLine = []
    speechStart = None
    for line in pages[tuplesStart:]:
        if line == 'START3':
            # determines where to start recreating speech text
            speechStart = pages.index(line)
            break
        if line == 'START2':
            continue
        elif line == 'END2':
            allPagesDraw.append(pageDraw)
            pageDraw = []
        else:
            if line == ',,,':
                vals = [None, None, None, None]
            else:
                vals = line.split(',')
            for i in range(len(vals)):
                if (vals[i] != None) and (i != 3) and (len(vals) == 4):
                    vals[i] = float(vals[i])
            tup = tuple(vals)
            if len(tup) == 4:
                pageDraw.append(tup)
    allSpeechPages = []
    imageStart = None
    # recreates speech text from saved file
    for speechPage in pages[speechStart:]:
        if speechPage == 'START4':
            # determines where to start recreating images
            imageStart = pages.index(speechPage)
            break
        if speechPage != 'START3' and speechPage != 'END3' and speechPage != "":
            allSpeechPages.append([speechPage])
    # recreates images from saved file
    allImagePages = []
    tableStart = None
    for page in pages[imageStart:]:
        if page == 'START5':
            tableStart = pages.index(page)
            break
        if page == 'START4':
            imagePage = []
            continue
        if page == 'END4':
            allImagePages.append(imagePage)
            continue
        else:
            picture = []
            # convert string of image corner coordinates into lists as they
            # were in the original image data
            coordList = []
            for elem in page.split(','):
                if page.split(',').index(elem) < 4:
                    newElem = ''
                    for char in elem:
                        if char.isdigit():
                            newElem += char
                    newElem = int(newElem)
                    coordList.append(newElem)
                    if len(coordList) == 2:
                        picture.append(coordList)
                        coordList = []
                # recreates the rest of the image data
                elif page.split(',').index(elem) == 4:
                    picture.append(None)
                else:
                    picture.append(elem)
            imagePage.append(picture)
    # recreates tables from saved file
    allTablesPages = []
    for page in pages[tableStart:]:
        if page == '':
            break
        if page == 'START5':
            tablePage = []
            continue
        if page == 'END5':
            allTablesPages.append(tablePage)
            continue
        else:
            oneTable = []
            tableComponents = page.split(' ■table')
            tableCells = eval(tableComponents[0][:-1])
            tableCells = eval(tableCells)
            tableID = ' ■table'+tableComponents[-1]
            oneTable.append(tableCells)
            oneTable.append(tableID)
            tablePage.append(oneTable)
    return allPages, allPagesDraw, allSpeechPages, allImagePages, allTablesPages

# recording function from: https://www.youtube.com/watch?v=K_WbsFrPUCk  
# returns string of recording
def recorder():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            return text
        except:
            return None

# recreates and returns the word a selected character belongs to
def charToWord(row, col, page):
    if page[row][col] == None:
        return None
    # determines that a word was not clicked
    if (not page[row][col][0].isalpha()) and (page[row][col][0] != "'"):
        return None
    firstHalf = []
    # go backwards from character to get the first half of the word
    if col != 0:
        for i in range(col, -1, -1):
            if page[row][i] == None:
                break
            if 'image' in page[row][i]:
                break
            if page[row][i][0].isalpha() or page[row][i][0] == "'":
               firstHalf.append(page[row][i][0])
            else:
                break
        firstHalf = firstHalf[::-1]
    # opposite process to get the other half of the word
    secondHalf = []
    if col != 55:
        for j in range(col, 56):
            if page[row][j] == None:
                break
            if 'image' in page[row][j]:
                break
            if page[row][j][0].isalpha() or page[row][j][0] == "'":
               secondHalf.append(page[row][j][0])
            else:
                break
    if firstHalf != [] and secondHalf != None:
        secondHalf = secondHalf[1:]
    return firstHalf+secondHalf

# edits selected text based on different actions, returns page of edited text
def changeText(corners, page, action):
    # reverses corners if the topLeft is in the place of the bottomRight
    if ((corners[0][0] > corners[1][0]) or 
                (corners[0][1] > corners[1][1])):
                corners = corners[::-1]
    if action == 'Delete':
        for row in range(corners[0][0], corners[1][0]+1):
            for col in range(corners[0][1], corners[1][1]):
                # prevents hidden table text representation deletion
                if (not page[row][col]==None and not 'table' in page[row][col]):
                    page[row][col] = None
    if action == 'Bold' or action == 'unBold': tag = ' b'
    if action == 'Italic' or action == 'unItalic': tag = ' i'
    # adds a string tag indicating bolding or italiscizing to selected text
    if action == 'Bold' or action == 'Italic':
        for row in range(corners[0][0], corners[1][0]+1):
            for col in range(corners[0][1], corners[1][1]):
                if page[row][col] == None:
                    continue
                else:
                    if (not tag in page[row][col] and 
                       not 'image' in page[row][col] and
                       not 'table' in page[row][col]):
                        page[row][col] += tag    
    # removes the bold string tag or italic string tag from selected text
    if action == 'unBold' or action == 'unItalic':
        for row in range(corners[0][0], corners[1][0]+1):
            for col in range(corners[0][1], corners[1][1]):
                if page[row][col] == None:
                    continue
                else:
                    if tag in page[row][col]:
                        page[row][col] = page[row][col].replace(tag, '')
    if action == 'Underline' or action == 'unUnderline': tag = ' u1'
    if action == 'Overstrike' or action == 'unOverstrike': tag = ' o1'
    # adds a string tag indicating underlining or overstriking to selected text
    if action == 'Underline' or action == 'Overstrike':
        for row in range(corners[0][0], corners[1][0]+1):
            for col in range(corners[0][1], corners[1][1]):
                if page[row][col] == None:
                    continue
                else:
                    if ((not tag in page[row][col]) and 
                        (not ' uo' in page[row][col]) and
                        (not 'image' in page[row][col]) and
                        (not 'table' in page[row][col])):
                        page[row][col] += tag    
    # removes the underline or overstrike string tag from selected text
    if action == 'unUnderline' or action == 'unOverstrike':
        for row in range(corners[0][0], corners[1][0]+1):
            for col in range(corners[0][1], corners[1][1]):
                if page[row][col] == None:
                    continue
                else:
                    if tag in page[row][col] or ' uo' in page[row][col]:
                        page[row][col] = page[row][col].replace(tag, '')
                        page[row][col] = page[row][col].replace(' uo', '')
    return page

# returns row and col of either left, top corner of selected text or
# row and col of right, bottom corner of selected text
def textCorners(x, y, width, page):
    # returns None, None if the click was out of the notebook page
    if (x < width/2.5+32) or (y < 60) or (x > 1200) or (y > 690):
        return None, None
    else: 
        # converts the x and y coordinates to the row and column on the page
        row = int(int(y)/30 - 2)
        colArea = width - (width/2.5+32)
        colSpace = colArea/56
        col = int((x - width/2.5+32)/colSpace)-5
    if row > 20:
        row = 20
    if col > 56:
        col = 56
    return row, col

# returns a word that is clicked on 
def getWord(x, y, width, page):
    (row, col) = textCorners(x, y, width, page)
    if ((row, col) == (None, None) or 
        page[row][col] == None or 
        'image' in page[row][col]):
        return
    else:
        return charToWord(row, col, page)

# creates and returns a dictionary showing the locations of every typo
def findTypos(page):    
    typos = {}
    readingWord=False
    currWordStart=None
    currWordEnd=None
    for r in range(21):
        typos[r]=[]
        for c in range(56):
            # determines the end of a word
            if (page[r][c]==None or page[r][c][0]==' ' or 
                'image' in page[r][c] or 'table' in page[r][c] or 
                page[r][c][0] in {'.', ',', '!', ':', ';', '"'}):
                readingWord=False
                if currWordStart != None and currWordEnd != None:
                    formWord = ''
                    for charI in range(currWordStart, currWordEnd+1):
                        if page[r][charI]==None: continue
                        formWord += page[r][charI][0]
                    # determines if a word is a typo by seeing if it is not in
                    # common English or if the word is somehow blank or a 
                    # bullet or a number
                    if (not formWord.lower() in commonWords and 
                        not formWord.strip()=='' and
                        not formWord=='●' and
                        not formWord.isdigit()):
                        typos[r].append((currWordStart, currWordEnd))
                    currWordStart=None
                    currWordEnd=None
            elif currWordStart==None:
                currWordStart=c
                currWordEnd=c+1
            if currWordStart != None:
                currWordEnd=c
    return typos

# pickle method learned from:
# https://pythonprogramming.net/python-pickle-module-save-objects-serialization/
# downloaded from: https://github.com/dwyl/english-words/blob/master/words.txt  
dictionary = pickle.load(open('words.pkl', 'rb'))
# downloaded from: https://gist.github.com/h3xx/1976236
commonWords = pickle.load(open('moreCommonWords.pkl', 'rb'))

# ideas for autocorrect() and its helper functions from:
# https://medium.com/@willsentance/how-to-write-your-own-spellchecker-and-
# autocorrect-algorithm-in-under-80-lines-of-code-6d65d21bb7b6
# returns the correct spelling of an inputted word
def autocorrect(word):
    word = word.lower()
    if word in dictionary and word in commonWords:
        return word
    (error1, error2) = errorDistance1(word), errorDistance2(word)
    # words so common that are almost absolutely spelled right
    if not len(error1) == 0:
        if error1[0] in error2:
            return error1[0]
    # make decisions more complex and account for correct spellings
    if not len(error1) == 0:
        return error1[0]
    # accounts for less used but correctly spelled words if common word
    # replacements do not exist
    if len(error2) != 0:
        return error2[0]
    return None

# retrieves one character off correct word possibilities
def errorDistance1(word):
    realWords1 = []
    likelyWords1 = []
    if ((word in dictionary) and (word in commonWords)
       and (commonWords[word] <= 20000)):
       return word
    mistake1 = addLetter(word)
    mistake2 = removeLetter(word)
    mistake3 = substituteLetter(word)
    mistake4 = adjacentSwaps(word)
    realWords1.extend(mistake1)
    realWords1.extend(mistake2)
    realWords1.extend(mistake3)
    realWords1.extend(mistake4)
    for word in set(realWords1):
        if word in commonWords:
            likelyWords1.append(word)
    # sort words based on how commonly used they are
    likelyWords1 = quickSort(likelyWords1)
    if len(realWords1) < 3:
        return realWords1
    return likelyWords1

# all possibilities of adding one letter to any index of a word
def addLetter(word):
    combinations = []
    for i in range(len(word)+1):
        for alphabet in string.ascii_lowercase:
            newWord = word[:i]+alphabet+word[i:]
            if newWord in dictionary:
                combinations.append(newWord)
    return combinations

# all possibilities of removing one letter from a word
def removeLetter(word):
    combinations = []
    for i in range(len(word)):
        if not i == len(word):
            newWord = word[:i]+word[i+1:]
        else:
            newWord = word[:i]
        if newWord in dictionary:
            combinations.append(newWord)
    return combinations

# all possibilities of substituting a letter with any letter in the alphabet
# in any index of the word
def substituteLetter(word):
    combinations = []
    for i in range(len(word)):
        for alphabet in string.ascii_lowercase:
            newWord = word[:i]+alphabet+word[i+1:]
            if newWord in dictionary:
                combinations.append(newWord)
    return combinations

# all possibilities of swapping characters next to each other in a word
def adjacentSwaps(word):
    combinations = []
    for i in range(len(word)-1):
        swap1 = word[i] 
        swap2 = word[i+1]
        end = word[i+2:]
        newWord = word[:i]+swap2+swap1+end
        if newWord in dictionary:
            combinations.append(newWord)
    return combinations

# retrieves all correct word possibilities two characters off from the typo
def errorDistance2(word):
    realWords2 = []
    likelyWords2 = []
    if ((word in dictionary) and (word in commonWords)
       and (commonWords[word] <= 20000)):
       return word
    mistake1 = addLetter2(word)
    mistake2 = removeLetter2(word)
    mistake3 = substituteLetter2(word)
    mistake4 = adjacentSwaps2(word)
    realWords2.extend(mistake1)
    realWords2.extend(mistake2)
    realWords2.extend(mistake3)
    realWords2.extend(mistake4)
    for word in set(realWords2):
        if word in commonWords:
            likelyWords2.append(word)
    likelyWords2 = quickSort(likelyWords2)
    if len(realWords2) <= 3:
        return realWords2
    return likelyWords2

# adds all two letter combinations at all indexes of the word
def addLetter2(word):
    combinations = []
    for i in range(len(word)+1):
        for alphabet1 in string.ascii_lowercase:
            for alphabet2 in string.ascii_lowercase:
                newWord = word[:i]+alphabet1+alphabet2+word[i:]
                if newWord in dictionary:
                    combinations.append(newWord)
    return combinations

# removes two letters from all possible indexes of the word
def removeLetter2(word):
    combinations = []
    for i in range(len(word)-1):
        if not i == len(word):
            newWord = word[:i]+word[i+2:]
        else:
            newWord = word[:i]
        if newWord in dictionary:
            combinations.append(newWord)
    return combinations

# substitutes a letter with all two letter combinations on all indexes
def substituteLetter2(word):
    combinations = []
    for i in range(len(word)):
        for alphabet1 in string.ascii_lowercase:
            for alphabet2 in string.ascii_lowercase:
                newWord = word[:i]+alphabet1+alphabet2+word[i+1:]
                if newWord in dictionary:
                    combinations.append(newWord)
    return combinations

# swaps two characters to an adjacent character for every possible combinations
def adjacentSwaps2(word):
    combinations = []
    for i in range(len(word)-1):
        swap1 = word[i] 
        swap2 = word[i+1:i+3]
        if len(swap2) != 2:
            break
        end = word[i+3:]
        newWord = word[:i]+swap2+swap1+end
        if newWord in dictionary:
            combinations.append(newWord)
    return combinations

# minimally adapted quickSort (compares dictionary values here) from:
# https://www.cs.cmu.edu/~112/notes/notes-recursion-part1.html#quicksort
def quickSort(L):
    if (len(L) < 2):
        return L
    else:
        first = L[0]  
        rest = L[1:]
        lo = [x for x in rest if commonWords[x] < commonWords[first]]
        hi = [x for x in rest if commonWords[x] >= commonWords[first]]
        return quickSort(lo) + [first] + quickSort(hi)

# webscrapes an online dictionary to return the list of definitions of a word
# webscrapes definitions from: www.vocabulary.com   
def getDefinitions(word):
    url = 'https://www.vocabulary.com/dictionary/'+word
    r = requests.get(url)
    #soup parsing technique adapted from: 
    # https://www.youtube.com/watch?v=aIPqt-OdmS0
    soup = BeautifulSoup(r.content, 'lxml')
    definitions = soup.find_all('h3', class_='definition')
    definitionsList = []
    for d in definitions:
        # cleans definitions to be more readable
        definition = str(d)
        wordType = None
        titleIndex = definition.index('title="')
        definition = definition[titleIndex+len('title="'):-5]
        cutOutType = definition.index('"')
        wordType = definition[:cutOutType]+':'
        definition = definition[cutOutType+10:].strip()
        definitionsList.append(wordType+' '+definition)
    return definitionsList

# finds out and returns where a line turns blank before reaching a sentence 
# word limit to cleanly splice and display text lines for dictionary definitions
def tailBlank(text):
    index = None
    while index == None:
        for i in range(len(text)-1, 0, -1):
            if text[i] == ' ':
                index = i
                break
        break
    return index

# various math symbol characters from:
# https://www.rapidtables.com/math/symbols/Basic_Math_Symbols.html
# replaces 'aprx' on a page with '≈':
def findAprx(page, row):
    for i in range(len(page[row])):
        if page[row][i] == None:
            continue
        # determines that 'aprx' is there for the edges of the page
        if (page[row][0] != None and page[row][1] != None and
            page[row][2] != None and page[row][3] != None):
            # all capital/lowecase letter spellings of 'aprx' count
            if (page[row][0][0].lower()=='a' and 
                page[row][1][0].lower()=='p' and
                page[row][2][0].lower()=='r' and
                page[row][3][0].lower()=='x' and
                (page[row][4]==None or page[row][4][0]==' ')):
                page[row][1]='≈'+page[row][i+3][1:]
                page[row][0]=' '+page[row][i][1:]
                page[row][2]=' '+page[row][i+2][1:]
                page[row][3]=' '+page[row][i+1][1:]
        # determines that 'aprx' is there to swap with '≈'
        if (page[row][i][0].lower() == 'a' and not i+3 > 55 and
            not i-1 < 0):
            if page[row][i+1]==None: 
                continue
            elif (page[row][i+1][0].lower()=='p' and
                  page[row][i+2][0].lower()=='r' and
                  page[row][i+3][0].lower()=='x' and                  
                  (page[row][i-1]==None or page[row][i-1][0]==' ' )):
                page[row][i]='≈'+page[row][i+3][1:]
                page[row][i+1]=' '+page[row][i+1][1:]
                page[row][i+2]=' '+page[row][i+2][1:]
                page[row][i+3]=' '+page[row][i][1:]

# replaces 'root' on a page with '√'
def findRoot(page, row):
    for i in range(len(page[row])):
        if page[row][i] == None:
            continue
        # determines that 'root' is there for the edges of the page
        if (page[row][0] != None and page[row][1] != None and
            page[row][2] != None and page[row][3] != None):
            # all capital/lowecase letter spellings of 'root' count
            if (page[row][0][0].lower()=='r' and 
                page[row][1][0].lower()=='o' and
                page[row][2][0].lower()=='o' and
                page[row][3][0].lower()=='t' and
                (page[row][4]==None or page[row][4][0]==' ')):
                page[row][3]='√'+page[row][i+3][1:]
                page[row][0]=' '+page[row][i][1:]
                page[row][1]=' '+page[row][i+1][1:]
                page[row][2]=' '+page[row][i+2][1:]
        # determines that 'root' is there to swap with '√'
        if (page[row][i][0].lower() == 'r' and not i+3 > 55 and
            not i-1 < 0):
            if page[row][i+1]==None: 
                continue
            elif (page[row][i+1][0].lower()=='o' and
                  page[row][i+2][0].lower()=='o' and
                  page[row][i+3][0].lower()=='t' and                  
                  (page[row][i-1]==None or page[row][i-1][0]==' ' )):
                page[row][i+3]='√'+page[row][i+3][1:]
                page[row][i]=' '+page[row][i][1:]
                page[row][i+1]=' '+page[row][i+1][1:]
                page[row][i+2]=' '+page[row][i+2][1:]

# replaces 'pi' on a page with 'π'
def findPi(page, row):
    for i in range(len(page[row])):
        if page[row][i] == None:
            continue
        # determines 'pi' is there for edges of the page
        if page[row][0] != None and page[row][1] != None:
            # all capital/lowecase letter spellings of 'pi' count
            if (page[row][0][0].lower()=='p' and 
                page[row][1][0].lower()=='i' and
                (page[row][2]==None or page[row][2][0]==' ')):
                page[row][0]='π'+page[row][i+1][1:]
                page[row][1]=' '+page[row][i+1][1:]
        # determines that 'pi' is there to swap with 'π'
        if (page[row][i][0].lower() == 'p' and not i+1 > 55 and
            not i-1 < 0):
            if page[row][i+1]==None: 
                continue
            elif (page[row][i+1][0].lower()=='i' and 
                  (page[row][i-1]==None or page[row][i-1][0]==' ' )):
                page[row][i]='π'+page[row][i+1][1:]
                page[row][i+1]=' '+page[row][i+1][1:]

# exponent text characters generated from:
# https://lingojam.com/SuperscriptGenerator
# replaces numbers with an exponent format of themselves
def powers(page, row):
    nums=['⁰','¹','²','³','⁴','⁵','⁶','⁷','⁸','⁹']
    stopPower = False
    for i in range(len(page[row])):
        if page[row][i] != None and page[row][i][0]=='^':
            while not stopPower:
                for j in range(i+1, 56):
                    # determines the end of an exponent
                    if page[row][j]==None:
                        stopPower=True
                        break
                    if page[row][j][0] not in '0123456789':
                        if page[row][j-1][0] in '0123456789':
                            page[row][j-1]=' '+page[row][j-1][1:]
                        stopPower=True
                        break
                    # write the exponent form
                    else:
                        num=nums[int(page[row][j][0])]
                        # back one character to delete the original format '^'
                        page[row][j-1]=num+page[row][j-1][1:]
                        if j+1 < 56 and page[row][j+1] not in nums:
                            page[row][j]=' '+page[row][j][1:]
                        elif j==55:
                            page[row][j]=' '+page[row][j][1:]
                stopPower=True

# notebook and all of its features
# uses bullet point and arrow text characters from:
# https://bizuns.com/symbols-bullets-copy-paste
class NoteBookMode(Mode):
    # learned how to use buttons from:
    # https://effbot.org/tkinterbook/button.htm   
    def keyboard(mode):
        keyboard = Toplevel()
        keyboard.title('Keyboard')
        keyboard.geometry('498x211')
        # all buttons call keyPressed function with the character that would
        # otherwise be in the event key (simulates typing)
        # first row of keyboard
        B = Button(keyboard, text='~', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '~'))
        B.place(x=0, y=0)
        B = Button(keyboard, text='!', width=3, height=2,
                   command=lambda: NoteBookMode.keyPressed(mode, '!'))
        B.place(x=30, y=0)
        B = Button(keyboard, text='@', width=3, height=2,
                   command=lambda: NoteBookMode.keyPressed(mode, '@'))
        B.place(x=60, y=0)
        B = Button(keyboard, text='#', width=3, height=2,
                   command=lambda: NoteBookMode.keyPressed(mode, '#'))
        B.place(x=90, y=0)
        B = Button(keyboard, text='$', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '$'))
        B.place(x=120, y=0)
        B = Button(keyboard, text='%', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '%'))
        B.place(x=150, y=0)
        B = Button(keyboard, text='^', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '^'))
        B.place(x=180, y=0)
        B = Button(keyboard, text='&', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '&'))
        B.place(x=210, y=0)
        B = Button(keyboard, text='*', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '*'))
        B.place(x=240, y=0)
        B = Button(keyboard, text='(', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '('))
        B.place(x=270, y=0)
        B = Button(keyboard, text=')', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, ')'))
        B.place(x=300, y=0)
        B = Button(keyboard, text='_', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '_'))
        B.place(x=330, y=0)
        B = Button(keyboard, text='+', width=3, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, '+'))
        B.place(x=360, y=0)
        B = Button(keyboard, text='Delete', width=6, height=2,
                       command=lambda: NoteBookMode.keyPressed(mode, 'Delete'))
        B.place(x=390, y=0)
        # second row of keyboard
        B = Button(keyboard, text='`', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '`'))
        B.place(x=0, y=35)
        B = Button(keyboard, text='1', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '1'))
        B.place(x=30, y=35)
        B = Button(keyboard, text='2', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '2'))
        B.place(x=60, y=35)
        B = Button(keyboard, text='3', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '3'))
        B.place(x=90, y=35)
        B = Button(keyboard, text='4', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '4'))
        B.place(x=120, y=35)
        B = Button(keyboard, text='5', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '5'))
        B.place(x=150, y=35)
        B = Button(keyboard, text='6', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '6'))
        B.place(x=180, y=35)
        B = Button(keyboard, text='7', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '7'))
        B.place(x=210, y=35)
        B = Button(keyboard, text='8', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '8'))
        B.place(x=240, y=35)
        B = Button(keyboard, text='9', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '9'))
        B.place(x=270, y=35)
        B = Button(keyboard, text='0', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '0'))
        B.place(x=300, y=35)
        B = Button(keyboard, text='-', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '-'))
        B.place(x=330, y=35)
        B = Button(keyboard, text='=', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '='))
        B.place(x=360, y=35)
        B = Button(keyboard, text='{', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '{'))
        B.place(x=390, y=35)
        B = Button(keyboard, text='}', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '}'))
        B.place(x=420, y=35)
        B = Button(keyboard, text='|', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '|'))
        B.place(x=450, y=35)
        # third row of keyboard
        B = Button(keyboard, text='tab', width=5, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Tab'))
        B.place(x=0, y=70)
        B = Button(keyboard, text='Q', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'q'))
        B.place(x=47, y=70)
        B = Button(keyboard, text='W', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'w'))
        B.place(x=77, y=70)
        B = Button(keyboard, text='E', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'e'))
        B.place(x=107, y=70)
        B = Button(keyboard, text='R', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'r'))
        B.place(x=137, y=70)
        B = Button(keyboard, text='T', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 't'))
        B.place(x=167, y=70)
        B = Button(keyboard, text='Y', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'y'))
        B.place(x=197, y=70)
        B = Button(keyboard, text='U', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'u'))
        B.place(x=227, y=70)
        B = Button(keyboard, text='I', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'i'))
        B.place(x=257, y=70)
        B = Button(keyboard, text='O', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'o'))
        B.place(x=287, y=70)
        B = Button(keyboard, text='P', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'p'))
        B.place(x=317, y=70)
        B = Button(keyboard, text='[', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '['))
        B.place(x=347, y=70)
        B = Button(keyboard, text=']', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, ']'))
        B.place(x=377, y=70)
        B = Button(keyboard, text='\\', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '\\'))
        B.place(x=407, y=70)
        B = Button(keyboard, text=';', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, ';'))
        B.place(x=437, y=70)
        B = Button(keyboard, text=':', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, ':'))
        B.place(x=467, y=70)
        # fourth row of keyboard
        B = Button(keyboard, text='caps lock', width=7, height=2, 
                   command=lambda: NoteBookMode.capsLockSwitch(mode))
        B.place(x=0, y=105)
        B = Button(keyboard, text='A', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'a'))
        B.place(x=66, y=105)
        B = Button(keyboard, text='S', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 's'))
        B.place(x=96, y=105)
        B = Button(keyboard, text='D', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'd'))
        B.place(x=126, y=105)
        B = Button(keyboard, text='F', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'f'))
        B.place(x=156, y=105)
        B = Button(keyboard, text='G', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'g'))
        B.place(x=186, y=105)
        B = Button(keyboard, text='H', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'h'))
        B.place(x=216, y=105)
        B = Button(keyboard, text='J', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'j'))
        B.place(x=246, y=105)
        B = Button(keyboard, text='K', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'k'))
        B.place(x=276, y=105)
        B = Button(keyboard, text='L', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'l'))
        B.place(x=306, y=105)
        B = Button(keyboard, text="'", width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, "'"))
        B.place(x=336, y=105)
        B = Button(keyboard, text='"', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '"'))
        B.place(x=366, y=105)
        B = Button(keyboard, text='enter', width=6, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Enter'))
        B.place(x=396, y=105)
        # fifth row of keyboard
        B = Button(keyboard, text='<', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '<'))
        B.place(x=0, y=140)
        B = Button(keyboard, text='>', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '>'))
        B.place(x=30, y=140)
        B = Button(keyboard, text='/', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '/'))
        B.place(x=60, y=140)
        B = Button(keyboard, text='Z', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'z'))
        B.place(x=90, y=140)
        B = Button(keyboard, text='X', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'x'))
        B.place(x=120, y=140)
        B = Button(keyboard, text='C', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'c'))
        B.place(x=150, y=140)
        B = Button(keyboard, text='V', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'v'))
        B.place(x=180, y=140)
        B = Button(keyboard, text='B', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'b'))
        B.place(x=210, y=140)
        B = Button(keyboard, text='N', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'n'))
        B.place(x=240, y=140)
        B = Button(keyboard, text='M', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'm'))
        B.place(x=270, y=140)
        B = Button(keyboard, text=',', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, ','))
        B.place(x=300, y=140)
        B = Button(keyboard, text='.', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '.'))
        B.place(x=330, y=140)
        B = Button(keyboard, text='?', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, '?'))
        B.place(x=360, y=140)
        B = Button(keyboard, text='↑', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Up'))
        B.place(x=437, y=140)
        # sixth row of keyboard
        B = Button(keyboard, text='space', width=24, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Space'))
        B.place(x=135, y=175)
        B = Button(keyboard, text='←', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Left'))
        B.place(x=407, y=175)
        B = Button(keyboard, text='↓', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Down'))
        B.place(x=437, y=175)
        B = Button(keyboard, text='→', width=3, height=2, 
                   command=lambda: NoteBookMode.keyPressed(mode, 'Right'))
        B.place(x=467, y=175)
        mainloop()

    # turns caps lock on or off, used for on screen keyboard
    def capsLockSwitch(mode):
        mode.capsLock = not mode.capsLock

    def appStarted(mode):
        # data structures
        mode.drawingTuples = [[]]
        mode.typedText = [[[None]*56 for i in range(21)]]
        mode.images = [[]]
        mode.speechNotes = [['']]
        # drawing tool settings
        mode.r = 2
        mode.lineWidth = 5
        mode.toolFill = 'Black'
        # trackers
        mode.onPage = 0
        mode.onSpeechPage = len(mode.speechNotes)-1
        mode.onCharacter = [0, 0]
        mode.selectedCorners = [(None, None), (None, None)]
        mode.selectedWord = None
        mode.correction = None
        mode.definitions = None
        mode.wordType = None
        mode.doubleClick = [(None, None), (None, None)]
        # actions
        mode.currentlyDrawing = False
        mode.usingEraser = False
        mode.eraser = (None, None)
        mode.recording = False
        mode.selectingWord = False
        mode.selectingText = False
        mode.bulleting = False
        mode.placingImage = False
        # sidescreen features
        mode.autoCorrect = False
        mode.defineWord = False
        mode.autoNotes = False
        # font modifications
        mode.bold = False
        mode.italic = False
        mode.underline = False
        mode.overstrike = False
        # image uploading, storing, and editing
        mode.imageToPlace = None
        mode.currentImage = None
        mode.scaledImage = None
        mode.imageSerialNum = 0
        mode.editImage = None
        mode.imageAction = None
        mode.visitedCoords = [None, None]
        mode.direction = [None, None]
        # table creating, storing, and editing
        mode.placingTable = False
        mode.tableSerialNum = 0
        mode.tables = [[]]
        mode.tableData = None
        mode.typingInTable = False
        mode.onTable = None
        mode.onTableRowCol = None
        mode.onCellIndex = None
        mode.cursorRowAndCol = [None, None]
        mode.tableEdit = None
        mode.tableEdited = False 
        # copy/cut/paste
        mode.copiedText = []
        # on-screen keyboard
        mode.capsLock = False
        # math characters
        mode.math = False
        mode.powerOf = False
        # typo finder
        mode.typos = {}
        mode.displayTypos = False
    
    # creates everything displayed on screen
    def redrawAll(mode, canvas):
        # draws the cursor based on where it is, makes it invisible if a table
        # is being typed in because that requires a different cursor system
        (row, col) = mode.onCharacter
        # draws highlight box of selected text
        if (mode.selectingText) and (not (None, None) in mode.selectedCorners):
            (top, left) = mode.selectedCorners[0]
            (bottom, right) = mode.selectedCorners[1]
            if mode.selectedCorners[0] > mode.selectedCorners[1]:
                # adjusts shape of selection box when moving selection upwards
                top += 1
                bottom -= 1
            canvas.create_rectangle(mode.width/2.5+32 + left*12, 60+top*30, 
                                    mode.width/2.5+32 + right*12, 90+bottom*30,
                                    fill='Lavender', outline='White')
        # show regular page cursor when a table isn't being typed in
        if not mode.typingInTable:
            canvas.create_line((mode.width/2.5 + 32 + col*12), 60 + (row*30), 
                               (mode.width/2.5 + 32 + col*12), 90 + (row*30),
                               fill='Steel Blue')
        # graphics for right side screen buttons
        buttonColors = ['Tomato2', 'Orange Red', 'Tomato2', 'OliveDrab1', 
                        'OliveDrab2', 'Cornflower Blue', 'Azure', 'Azure', 
                        'Black', 'Khaki1', 'Pink', 'MediumPurple2']
        labels = ['<', '', '>', 'Save', 'Open', 'Select', '', '', 'Pen', 
                  'Highlighter', 'Eraser', 'Size']
        for i in range(12):
            color = buttonColors[i]
            outline = color
            if i==5 and mode.selectingText: outline = 'Steel Blue'
            if i==8 and mode.currentlyDrawing and mode.toolFill=='Black':
                outline = 'Dark Slate Gray'
            if i==9 and mode.currentlyDrawing and mode.toolFill=='Yellow':
                outline = 'Goldenrod'
            if i==10 and mode.usingEraser:
                outline = 'Plum3'
            canvas.create_rectangle(mode.width-(6-i*0.5)*mode.width/10, 0, 
                                    mode.width-(5.5-i*0.5)*mode.width/10, 60, 
                                    fill=color, outline=outline, width=3)
            if i == 8: fill='White'
            else: fill='Black'
            canvas.create_text(mode.width-(5.75-i*0.5)*mode.width/10, 30, 
                               text=labels[i], font='Arial 11', fill=fill)
        # left side screen background
        canvas.create_rectangle(0, 0, mode.width/2.5, mode.height, fill='Green',
                                outline='Green')
        canvas.create_rectangle(30, 30, mode.width/2.5-30, mode.height-90,
                                   fill='White', outline='White')
        # left side screen button graphics
        canvas.create_rectangle(0, mode.height-60, mode.width/2.5, mode.height, 
                               fill='honeydew2', outline='honeydew2')
        buttonColors = ['Tomato2', 'Orange Red', 'Tomato2', 'SlateGray2', 
                        'SlateGray2', 'Thistle1', 'Thistle2', 'Thistle3']
        labels = ['<', '', '>', 'On-screen', 'Keyboard', 'Spelling', 
                  'Dictionary', 'Typos']
        for i in range(8):
            color = buttonColors[i]
            canvas.create_rectangle(mode.width/20*i, mode.height-60,
                                   mode.width/20+mode.width/20*i, mode.height,
                                   fill=color, outline=color)
            canvas.create_text(mode.width/20*i + mode.width/40, mode.height-30, 
                               text=labels[i], font='Arial 11')
        # recorded speech notes graphics
        if not mode.autoNotes:
            canvas.create_text(1.5*mode.width/20, mode.height-30, 
                          text=f'Autonotes', font = 'Arial 12')
        if mode.autoNotes:
            canvas.create_text(1.5*mode.width/20, mode.height-80, 
                          text=f'double-tap to record', font = 'Arial 12',
                               fill='Tomato')
            canvas.create_text(1.5*mode.width/20, mode.height-70, 
                          text=f'say, "stop recording" to quit', 
                               font = 'Arial 12', fill='Tomato')
            canvas.create_text(1.5*mode.width/20, mode.height-30, 
                          text=f'Pg. {mode.onSpeechPage+1}', font = 'Arial 12')
            canvas.create_rectangle(30, 30, mode.width/2.5-30, mode.height-90,
                                   fill='White', outline='White')
            # keeps track of lines while splitting the text string and 
            # placing it onto the page
            onLine = 0
            sentence = ''
            for word in mode.speechNotes[mode.onSpeechPage][0].split(' '):
                # determines if it's time to move to the next line
                if len(sentence+word+' ') >= 38:
                    canvas.create_text(36, 36+20*onLine, text=sentence, 
                                      anchor='nw', font='Courier 18')
                    sentence = (word+' ')
                    onLine += 1
                else:
                    sentence += (word+' ')
            if len(sentence) <= 38:
                canvas.create_text(36, 36+20*onLine, text=sentence, 
                                      anchor='nw', font='Courier 18')
        # graphics for spellcheck and dictionary screen
        if (mode.autoCorrect or mode.defineWord) and not mode.selectingText:
            margin = 30
            if (mode.autoCorrect) and (mode.selectedWord == None):
                canvas.create_text(40, 40, 
                                  text='Click on the word you want to correct.',
                                  anchor='nw', font='Arial 18')
            elif (mode.autoCorrect) and (mode.selectedWord != None):
                if mode.correction==None:
                    text = f'"{mode.selectedWord[:16]}..." is uncorrectable.'
                elif mode.correction==mode.selectedWord.lower():
                    text = f'You spelled "{mode.correction}" right.'
                else:
                    text = f'Try: "{mode.correction}"'
                canvas.create_text(40, 40,
                                  text=text,
                                  anchor='nw', font='Arial 18')
            if (mode.defineWord) and (mode.selectedWord == None):
                canvas.create_text(40, 40, 
                                  text='Click on the word you want to define.',
                                  anchor='nw', font='Arial 18')
            elif (mode.defineWord) and (mode.selectedWord != None):
                i = 0
                for definition in mode.definitions:
                    if i == 12:
                        break
                    if mode.wordType in definition:
                        text = definition
                    else:
                        continue
                    # splices long dictionary definitions into several lines
                    # if the definition is too long to fit into one line on its
                    # side of the screen
                    if len(definition) > 75:
                        # determines where to splice the line
                        chopIndex = tailBlank(definition[:75])
                        text1 = definition[:chopIndex+1]
                        text2 = definition[chopIndex+1:]
                        if len(text2) > 75:
                            chopIndex = tailBlank(text2[:75])
                            text3 = text2[chopIndex+1:]
                            text2 = text2[:chopIndex+1]
                            canvas.create_text(40, 104+40*i, text=text3, 
                                               anchor='nw', font='Arial 12')
                        canvas.create_text(40, 80+40*i, text=text1, anchor='nw',
                        font='Arial 12')
                        canvas.create_text(40, 92+40*i, text=text2, anchor='nw',
                        font='Arial 12')
                    elif len(definition) < 75:
                        canvas.create_text(40, 80+40*i, text=text, anchor='nw',
                        font='Arial 12')
                    i += 1
                if i > 0:
                    top=f'{mode.selectedWord}:'
                elif i == 0:
                    top='no available definitions'
                canvas.create_text(40, 40, 
                                  text=top, anchor='nw', font='Arial 16')
        # graphics for notebook lines
        canvas.create_line(mode.width/2.5+30, 60, mode.width/2.5+30, 
                           mode.height, fill='Red')
        lineCount = int(mode.height/30)+1
        for i in range(3, lineCount):
            canvas.create_line(mode.width/2.5, i*30, mode.width, i*30, 
                               fill='Blue')
        # draws table cell lines
        for table in mode.tables[mode.onPage]:
            if not table[0] == [] and not len(table[0][0])==2:
                colWidth = 56 / (len(table[0][0])-2)
                rows = len(table[0])
                colsPerRow = len(table[0][0])-2
                # create individual table cells as rectangles
                pageRef = mode.width/2.5+32
                for i in range(rows):
                    row = table[0][i]
                    for j in range(colsPerRow):
                        left=(row[0][1]+j*colWidth)*12+pageRef
                        top=(row[0][0])*(30)+61
                        right=(row[0][1]+j*colWidth+colWidth)*12+pageRef
                        bottom=(row[-1][0])*(30)+61
                        canvas.create_rectangle(left, top, right, bottom, 
                                                width=2, outline='RoyalBlue3')
        # graphics for any underlines or overstrikes placed on text
        for i in range(len(mode.typedText[mode.onPage])):
            drawingUnderline = False
            drawingOverstrike = False
            underlineStart = None
            overstrikeStart = None
            underlineEnd = None
            overstrikeEnd = None
            textWidth = mode.width - mode.width/2.5+32
            for j in range(len(mode.typedText[mode.onPage][i])):
                if mode.typedText[mode.onPage][i][j] == None:
                    continue
                # determines start and end of each underline and draws it
                if ((' u1' in mode.typedText[mode.onPage][i][j]) or 
                   (' uo' in mode.typedText[mode.onPage][i][j])):   
                    if not drawingUnderline:  
                        drawingUnderline = True
                        underlineStart = j
                    if ((drawingUnderline) and 
                       (j==55 or mode.typedText[mode.onPage][i][j+1] == None or 
                       (' u1' not in mode.typedText[mode.onPage][i][j+1] and
                       ' uo' not in mode.typedText[mode.onPage][i][j+1]))):
                       underlineEnd = j
                       drawingUnderline = False
                       canvas.create_line(mode.width/2.5+32 + underlineStart*12,
                                         88+i*30-3,
                                         mode.width/2.5+30 + underlineEnd*12+12,
                                         88+i*30-3, fill='Black', width=1.5)
                # determines start and end of each overstrike and draws it
                if ((' o1' in mode.typedText[mode.onPage][i][j]) or 
                   (' uo' in mode.typedText[mode.onPage][i][j])):   
                    if not drawingOverstrike:  
                        drawingOverstrike = True
                        overstrikeStart = j
                    if ((drawingOverstrike) and 
                       (j==55 or mode.typedText[mode.onPage][i][j+1] == None or 
                       (' o1' not in mode.typedText[mode.onPage][i][j+1] and
                       ' uo' not in mode.typedText[mode.onPage][i][j+1]))):
                       overstrikeEnd = j
                       drawingOverstrike = False        
                       canvas.create_line(mode.width/2.5+32+overstrikeStart*12,
                                         88+i*30-8,
                                         mode.width/2.5+30+overstrikeEnd*12+12,
                                         88+i*30-8, fill='Black', width=1.5)
        # graphics for typo highlighting
        if mode.displayTypos and mode.typos != {}:
            for row in mode.typos:
                if mode.typos[row]==[]:
                    continue
                for tup in mode.typos[row]:
                    x0 = mode.width/2.5+32+tup[0]*12
                    y0 = 90+row*30-6
                    x1 = mode.width/2.5+32+tup[1]*12+12
                    y1 = 90+row*30-6
                    canvas.create_line(x0, y0, x1, y1, fill='Red', width=3)
        # loads images on to the page
        if mode.images[mode.onPage] != []:
            for image in mode.images[mode.onPage]:
                # adjust image dimensions to page
                cx = image[0][1] + (image[1][1] - image[0][1])/2
                cy = image[0][0] + (image[1][0] - image[0][0])/2
                cx *= 12
                cy *= 30
                # fits image to its corners
                cx += mode.width/2.5+32
                cy += 60
                graphic = image[2]
                canvas.create_image(cx, cy, image=ImageTk.PhotoImage(graphic))
        # redraws all the line drawings made with pen/highlighter
        for i in range(len(mode.drawingTuples[mode.onPage])-1):
            (x, y, girth, fill) = mode.drawingTuples[mode.onPage][i]
            (x2, y2, girth, fill) = mode.drawingTuples[mode.onPage][i+1]    
            if not (((x, y) == (None, None) or (x2, y2) == (None, None))):
                canvas.create_line(x, y, x2, y2, width=girth, fill=fill)
                # circular tips make line look smoother for thicker lines
                if girth > 2:
                    canvas.create_oval(x-girth/2.5, y-girth/2.5,
                                    x+girth/2.5, y+girth/2.5,
                                    fill=fill, outline=fill)
                    canvas.create_oval(x2-girth/2.5, y2-girth/2.5,
                                    x2+girth/2.5, y2+girth/2.5,
                                    fill=fill, outline=fill)
        # graphic showing page user is on
        canvas.create_text(mode.width-5.25*mode.width/10, 30,
                          text=f'Pg. {mode.onPage+1}', font='Arial 12')
        # highlights whether certain features (e.g. bulleting) are in use
        if mode.bulleting: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(6-6*0.5)*mode.width/10, 0, 
                               mode.width-(5.5-5.5*0.5)*mode.width/10, 30,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-5.75*0.5)*mode.width/10-2, 15, 
                          text='b-list', font='Arial 9')
        if mode.math: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(6-6*0.5)*mode.width/10, 30, 
                               mode.width-(5.5-5.5*0.5)*mode.width/10, 60,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-5.75*0.5)*mode.width/10-2, 45, 
                          text='math', font='Arial 9')
        canvas.create_rectangle(mode.width-(6-6.5*0.5)*mode.width/10, 0, 
                               mode.width-(5.5-6*0.5)*mode.width/10, 30,
                               fill='Light Cyan', outline='Light Cyan', width=3)
        canvas.create_text(mode.width-(5.75-6.25*0.5)*mode.width/10-1, 15, 
                          text='table', font='Arial 9')
        canvas.create_rectangle(mode.width-(6-6.5*0.5)*mode.width/10, 30, 
                               mode.width-(5.5-6*0.5)*mode.width/10, 60,
                               fill='Light Cyan', outline='Light Cyan', width=3)
        canvas.create_text(mode.width-(5.75-6.25*0.5-0.01)*mode.width/10-1, 45, 
                          text='image', font='Arial 9')
        if mode.bold: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(6-7*0.5)*mode.width/10, 0, 
                               mode.width-(5.5-6.5*0.5)*mode.width/10, 30,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-6.75*0.5)*mode.width/10-1, 15, 
                          text='B', font='Arial 16 bold')
        if mode.italic: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(5.5-6.5*0.5)*mode.width/10, 0, 
                               mode.width-(5-6*0.5)*mode.width/10, 30,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-7.25*0.5)*mode.width/10, 15, 
                                      text='i', font='Arial 16 italic')
        if mode.underline: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(6-7*0.5)*mode.width/10, 30, 
                               mode.width-(5.5-6.5*0.5)*mode.width/10, 60,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-6.75*0.5)*mode.width/10-2, 45, 
                          text='u', font='Arial 16 underline')
        if mode.overstrike: color='LightSkyBlue3'
        else: color='Light Cyan'
        canvas.create_rectangle(mode.width-(5.5-6.5*0.5)*mode.width/10, 30, 
                               mode.width-(5-6*0.5)*mode.width/10, 60,
                               fill=color, outline=color, width=3)
        canvas.create_text(mode.width-(5.75-7.25*0.5)*mode.width/10, 45, 
                          text='st', font='Arial 16 overstrike')
        # draws the text the user has typed onto the page
        for i in range(len(mode.typedText[mode.onPage])):
            # separate text lines to separate bolded or italicized text
            # from default text
            text = ''
            boldText = ''
            italicText = ''
            boldAndItalicText = '' 
            for char in mode.typedText[mode.onPage][i]:
                # add to all text strings for all instances to keep line and
                # character spacing consistent 
                if (char != None and char and not ' b' in char and 
                    not ' i' in char):
                    text += char[0]
                    boldText += ' '
                    italicText += ' '
                    boldAndItalicText += ' '
                elif char == None:
                    char = ' '
                    text += ' '
                    boldText += ' '
                    italicText += ' '
                    boldAndItalicText += ' '
                if ' b' in char and not ' i' in char:
                    text += ' '
                    boldText += char[0]
                    italicText += ' '
                    boldAndItalicText += ' '
                if ' i' in char and not ' b' in char:
                    text+= ' '
                    italicText += char[0]
                    boldText += ' '
                    boldAndItalicText += ' '
                if ' i' in char and ' b' in char:
                    text += ' '
                    boldAndItalicText += char[0]
                    italicText += ' '
                    boldText += ' '
            canvas.create_text(mode.width/2.5+32, 78+30*i, text=text, 
                              anchor='w', font='Courier 20')
            canvas.create_text(mode.width/2.5+32, 78+30*i, text=boldText, 
                              anchor='w', font='Courier 20 bold')
            canvas.create_text(mode.width/2.5+32, 78+30*i, text=italicText, 
                              anchor='w', font='Courier 20 italic')
            canvas.create_text(mode.width/2.5+32, 78+30*i, 
                               text=boldAndItalicText, anchor='w', 
                               font='Courier 20 italic bold')
        # draws cursor when typing in tables
        if not mode.cursorRowAndCol == [None, None] and mode.typingInTable:
            cursorRow = mode.cursorRowAndCol[0]
            cursorCol = mode.cursorRowAndCol[1] 
            canvas.create_line(mode.width/2.5+32+ cursorCol, 60+cursorRow*30, 
                               mode.width/2.5+32+cursorCol, 90+cursorRow*30,
                               fill='Steel Blue')
        # draws typed text in tables
        if mode.tables[mode.onPage] != []:
            for table in mode.tables[mode.onPage]:
                if not table[0] == []:
                    tableCells = table[0]
                    colWidth = 56 / (len(tableCells[0])-2)
                    rowCoord = 78
                    for row in tableCells:
                        colCoord = mode.width/2.5+32
                        for cell in row[1:-1]:
                            if cell == []:
                                colCoord += colWidth*12
                                continue
                            startRow = row[0][0]
                            endRow = row[-1][0]
                            allCellText = ''
                            for char in cell:
                                allCellText += char
                            onLine = 0
                            preSplice = int(colWidth)*onLine
                            textSplice = int(colWidth)*(onLine+1)
                            for r in range(startRow, endRow):
                                text = allCellText[preSplice:textSplice]
                                x = colCoord 
                                y = r*30+rowCoord
                                canvas.create_text(x, y, text=text, anchor='w', 
                                                   font='Courier 20')
                                # update text splices going down cell text
                                onLine += 1
                                preSplice = int(colWidth)*onLine
                                textSplice = int(colWidth)*(onLine+1)
                            colCoord += colWidth*12
        # draws the eraser as it is being used        
        if mode.usingEraser:
            (x, y) = mode.eraser
            r = 3*mode.lineWidth
            if (x, y) != (None, None):
                canvas.create_oval(x-r, y-r, x+r, y+r, fill='Hot Pink', 
                                   outline='Hot Pink')

    # shuts all features off to prevent feature conflicts when turning on 
    # certain features afterwards
    def turnEverythingOff(mode):
        mode.selectingText = False
        mode.selectingWord = False
        mode.currentlyDrawing = False
        mode.usingEraser = False
        mode.selectingWord = False
        mode.placingTable = False
        mode.typingInTable = False
        mode.autoCorrect = False
        mode.defineWord = False
        mode.autoNotes = False
        mode.displayTypos = False
        mode.typos = {}

    # table editing (adding/deleting rows and columns)          
    def tableChoice(mode, choice, tRow, tCol, row):
        # avoids out of index errors once tables are fully deleted
        if (mode.onTable==None or 
            mode.tables[mode.onPage][mode.onTable]==[] or
            mode.tables[mode.onPage][mode.onTable][0]==[]): return
        mode.tableEdit = choice
        if mode.onTable > len(mode.tables[mode.onPage]): return
        table = mode.tables[mode.onPage][mode.onTable]
        tableTag = mode.tables[mode.onPage][mode.onTable][1]
        mode.typedText[mode.onPage] = cleanTable(mode.typedText[mode.onPage], 
                                                 tableTag)
        tRep = [mode.tables[mode.onPage][mode.onTable][0] for i in range(1)][0]
        # edit the table
        tableChange = editTable(mode.typedText[mode.onPage], tRep,
                                choice, tRow, tCol, table, row,
                                mode.images[mode.onPage],
                                mode.tables[mode.onPage])
        mode.typedText[mode.onPage] = tableOnText(mode.typedText[mode.onPage], 
                                                  table)
        # gets rid of a table's data structure when all cells are destroyed
        if (mode.tables[mode.onPage][mode.onTable][0] == [] or
            len(mode.tables[mode.onPage][mode.onTable][0][0]) == 2):
            cleanTable(mode.typedText[mode.onPage], tableTag)
            mode.tables[mode.onPage].pop(mode.onTable)
            mode.onTable==None
            
    # console for editing table
    def tableOptions(mode, tRow, tCol, row):
        tOptions = Toplevel()
        tOptions.title('')
        B = Button(tOptions, text='Insert Row', width=12, height=2,
                   command=lambda: NoteBookMode.tableChoice(mode, 'InsertRow', 
                                                            tRow, tCol, row))
        B.pack()
        B = Button(tOptions, text='Delete Row', width=12, height=2,
                   command=lambda: NoteBookMode.tableChoice(mode, 'DeleteRow', 
                                                            tRow, tCol, row))
        B.pack()
        B = Button(tOptions, text='Insert Col', width=12, height=2,
                   command=lambda: NoteBookMode.tableChoice(mode, 'InsertCol', 
                                                            tRow, tCol, row))
        B.pack()
        B = Button(tOptions, text='Delete Col', width=12, height=2,
                   command=lambda: NoteBookMode.tableChoice(mode, 'DeleteCol', 
                                                            tRow, tCol, row))
        B.pack()
        
    # all actions from pressing the mouse
    def mousePressed(mode, event):
        x = event.x
        y = event.y
        # registers double clicks (used for opening table edit options)
        mode.doubleClick[1] = mode.doubleClick[0]
        mode.doubleClick[0] = (event.x, event.y)
        # finds notebook page location of a click
        (row, col) = textCorners(x, y, mode.width, mode.typedText[mode.onPage])
        # return to regular typing
        mode.typingInTable = False
        # determines where to place a table 
        # (makes sure clicks are in notebook bounds)
        if mode.placingTable and y >= 60 and x > mode.width/2.5+32:
            (rows, cols) = mode.tableData
            table = makeTable(rows, cols, row, mode.tableSerialNum)
            if not legalTable(mode.typedText[mode.onPage], table):
                return
            mode.tables[mode.onPage].append(table)
            mode.typedText[mode.onPage]=tableOnText(mode.typedText[mode.onPage], 
                                                    table)
            mode.tableSerialNum += 1
            mode.placingTable = False
        # determines where to place an image
        if mode.placingImage and y >= 60 and x > mode.width/2.5+32:
            # ends image placement if other buttons/out of bounds areas clicked
            if (row, col) == (None, None):
                mode.placingImage = False
                return
            topLeft = list((row, col))
            image = mode.imageToPlace
            mode.currentImage = mode.loadImage(image)
            # scales image to format it for the notebook lines
            scale = 1/(mode.currentImage.size[0]/96)
            mode.scaledImage = mode.scaleImage(mode.currentImage, scale)
            height = mode.scaledImage.size[1]//30+1
            bottomRight = [topLeft[0]+height, topLeft[1]+8]
            # tag for text representation of image
            imageTag = ' image'+str(mode.imageSerialNum)
            imageData = [topLeft, bottomRight, mode.scaledImage, imageTag, 
                         image]
            # makes sure image placement does not interfere with text/images
            if legalImagePlacement(imageData, mode.typedText[mode.onPage]):
                mode.images[mode.onPage].append(imageData)
                mode.imageToPlace = None
                mode.imageSerialNum += 1
                mode.placingImage = False
            # creates text representations of images
            if not mode.images[mode.onPage] == []:
                resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
            return
        # select a table cell to start typing in
        if mode.tables[mode.onPage] != [] and y >= 60 and x > mode.width/2.5+32:
            if (row != None and col != None and row < 21 and col < 56 and
                mode.typedText[mode.onPage][row][col] != None and 
                'table' in mode.typedText[mode.onPage][row][col]):
                mode.typingInTable = True
                tableTag = mode.typedText[mode.onPage][row][col]
                mode.onTable = whichTable(mode.tables[mode.onPage], tableTag)
                if mode.onTable==None: return
                RowColInfo=whichCell(mode.tables[mode.onPage][mode.onTable][0],
                                             row, col)
                mode.onTableRowCol=RowColInfo
                tRow = mode.onTableRowCol[0]
                tCol = mode.onTableRowCol[1]
                # when the user double clicks, they can add/delete rows and cols
                if mode.doubleClick[0] == mode.doubleClick[1]:
                    NoteBookMode.tableOptions(mode, tRow, tCol, row)
                    mode.typingInTable = False
                    return
                # determines which index to start typing on in the cell
                r = mode.onTableRowCol[0]
                c = mode.onTableRowCol[1]
                cell = mode.tables[mode.onPage][mode.onTable][0][r][c]
                # makes it such that the user starts typing at the end of a
                # string in the cell being typed in
                mode.onCellIndex = len(cell)
        if mode.selectingText and y >= 60 and x > mode.width/2.5+32:
            # actions for clicking/resizing an image
            if mode.images[mode.onPage] != []:
                # checks that an image was clicked
                if (row != None and col != None and row < 21 and col < 56 and
                    (mode.typedText[mode.onPage][row][col] != None) and
                    ('image' in mode.typedText[mode.onPage][row][col])):
                    # determines the index of a number on the page and what
                    # will be done to the image (resizing or moving)
                    whichImage = mode.typedText[mode.onPage][row][col]
                    (imageIndex, editType) = getImageData(whichImage, 
                                                       mode.images[mode.onPage],
                                                       row, col)
                    mode.editImage = imageIndex
                    mode.imageAction = editType
                    return
            # resets selected corners every time there is a click
            mode.selectedCorners[0] = (row, col)
            if row != None: mode.onCharacter[0] = row
            if col != None: mode.onCharacter[1] = col
            mode.selectedCorners[1] = (None, None)
            return
        # table placement on
        if ((mode.width-(6-6.5*0.5)*mode.width/10 < x  and 
            x < mode.width-(5.5-6*0.5)*mode.width/10) and
            (0 < y < 30)):
            NoteBookMode.turnEverythingOff(mode)
            mode.placingTable = True
            # determine table dimensions
            mode.tableData = 'Enter table dimensions (rows, cols)'
            mode.tableData = mode.getUserInput(mode.tableData)
            if mode.tableData == None:
                mode.placingTable = False
                return
            # prevents a crash that would evaluate a letter and consider it a
            # non-existing variable
            for char in mode.tableData:
                if (char in 'abcdefghijklmnopqrstuvwxyz' or
                    char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
                    mode.placingTable = False
                    return
            # converts input string to a list of coordinates
            mode.tableData = eval(mode.tableData)
            mode.tableData = list(mode.tableData)
            # cancels for unreadable inputs
            if ((not len(mode.tableData)==2) or 
                (not isinstance(mode.tableData[0], int)) or
                (not isinstance(mode.tableData[1], int))):
                mode.placingTable = False
            # set limits for how many cells a table can have
            if mode.tableData[0] > 20: mode.tableData[0] = 20
            if mode.tableData[1] > 12: mode.tableData[1] = 12
        # bulleted list on and off
        if ((mode.width-(6-6*0.5)*mode.width/10 < x and 
            x < mode.width-(5.5-5.5*0.5)*mode.width/10) and
            (0 < y < 30)):
            mode.bulleting = not mode.bulleting
            return
        # math symbols enabled for typing
        if ((mode.width-(6-6*0.5)*mode.width/10 < x and 
            x < mode.width-(5.5-5.5*0.5)*mode.width/10) and
            (30 < y < 60)):
            mode.math = not mode.math
            return
        # upload an image to be placed
        if ((mode.width-(6-6.5*0.5)*mode.width/10 < x and 
            x < mode.width-(5.5-6*0.5)*mode.width/10) and
            (30 < y < 60)):
            imageName = askopenfilename()
            # only image files can be opened
            if imageName[-4:] not in {'jpeg', '.jpg', '.gif', '.png'}:
                return
            mode.imageToPlace = imageName.split('/')[-1]
            NoteBookMode.turnEverythingOff(mode)
            mode.placingImage = True
            return
        # turn bold/italic/underline/overstrike on and off
        if ((mode.width-(6-7*0.5)*mode.width/10 < x and 
            x < mode.width-(5.5-6.5*0.5)*mode.width/10) and
           (0 < y < 30)):
           mode.bold = not mode.bold
           if ((mode.bold) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'Bold')
           if ((not mode.bold) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'unBold')
           return
        if ((mode.width-(5.5-6.5*0.5)*mode.width/10 < x and 
            x < mode.width-(5-6*0.5)*mode.width/10) and
           (0 < y < 30)):
           mode.italic = not mode.italic
           if ((mode.italic) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'Italic')
           if ((not mode.italic) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'unItalic')
           return
        if ((mode.width-(6-7*0.5)*mode.width/10 < x and 
            x < mode.width-(5.5-6.5*0.5)*mode.width/10) and
           (30 < y < 60)):
           mode.underline = not mode.underline
           if ((mode.underline) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'Underline')
           if ((not mode.underline) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'unUnderline')
           return
        if ((mode.width-(5.5-6.5*0.5)*mode.width/10 < x and 
            x < mode.width-(5-6*0.5)*mode.width/10) and
           (30 < y < 60)):
           mode.overstrike = not mode.overstrike
           if ((mode.overstrike) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'Overstrike')
           if ((not mode.overstrike) and (mode.selectingText) and
               (not (None, None) in mode.selectedCorners)):
               page = changeText(mode.selectedCorners, 
                                 mode.typedText[mode.onPage], 'unOverstrike')
           return
        # selects a character in a word then returns the word it belongs to
        if mode.selectingWord:
            #mode.currentlyDrawing = False
            #mode.usingEraser = False
            word = getWord(event.x, event.y, mode.width, 
                          mode.typedText[mode.onPage])
            if word != None:
                # asks for part of speech to make sure the screen isn't over
                # loaded with unwanted definitions
                if mode.defineWord:
                    pos = 'Enter part of speech (noun, verb, adjective, adverb)'
                    mode.wordType = mode.getUserInput(pos)
                    if mode.wordType == None:
                        mode.wordType = 'no type:'
                    else:
                        mode.wordType += ':'
                wordStr = ''
                for char in word:
                    wordStr += char
                # calls spellcheck and calls to webscrape word definitions
                mode.correction = autocorrect(wordStr)
                mode.definitions = getDefinitions(wordStr)
            else:
                wordStr = None
            mode.selectedWord = wordStr
        # turn on spellchecking use
        if ((5*mode.width/20 < x < 6*mode.width/20) and 
           (mode.height-60 < y < mode.height)):
           NoteBookMode.turnEverythingOff(mode)
           mode.autoCorrect = True
           mode.selectingWord = True
           mode.typos = {}
        # turn on dictionary use
        if ((6*mode.width/20 < x < 7*mode.width/20) and 
           (mode.height-60 < y < mode.height)):
           NoteBookMode.turnEverythingOff(mode)
           mode.defineWord = True
           mode.selectingWord = True
        # find typos/turn on typo display
        if ((7*mode.width/20 < x < 8*mode.width/20) and 
           (mode.height-60 < y < mode.height)):
           NoteBookMode.turnEverythingOff(mode)
           mode.autoCorrect = True
           mode.selectingWord = True
           mode.typos = findTypos(mode.typedText[mode.onPage])
           mode.displayTypos = True
        # starts recording 
        if ((2*mode.width/20 > x > mode.width/20) and 
           (mode.height > y > mode.height-60)):
           NoteBookMode.turnEverythingOff(mode)
           mode.autoNotes = True
           mode.onSpeechPage = len(mode.speechNotes)-1
           # must double click the button to turn on recording
           if mode.doubleClick[0]==mode.doubleClick[1]:
               mode.recording = True
           if mode.recording:
               speech = None
               while speech == None:
                   if speech == None:
                       # keeps calling recorder to keep recording going longer
                       speech = recorder()
                   # allows recording loop to be exited when the user
                   # literally says, "stop recording"
                   if speech == "stop recording":
                       mode.recording = False
                       break
                   if speech != None:
                       pageChars = len(mode.speechNotes[-1][0]) + len(speech)
                       # determines which page to place text on and how long
                       # one page's text can be
                       if pageChars >= (24*38):
                           mode.speechNotes.append([''])
                           mode.onSpeechPage += 1
                       mode.speechNotes[-1][0] += (speech+' ')
                   speech = None   
        # change the size of pen/highlighter/eraser     
        if ((mode.width > x > mode.width-0.5*mode.width/10) and (60 > y > 0)):
           mode.currentlyDrawing = False
           mode.usingEraser = False
           lineWidthChange = mode.getUserInput('Enter a size between 1 and 14.')
           if (lineWidthChange != None) and (lineWidthChange.isdigit()):
               if int(lineWidthChange) > 14:
                   lineWidthChange = 14
               mode.lineWidth = int(lineWidthChange)
        # turn eraser/highlighter//pen on and off
        if ((mode.width-0.5*mode.width/10 > x > mode.width-mode.width/10) and
           (60 > y > 0)):
           mode.toolFill = None
           NoteBookMode.turnEverythingOff(mode)
           mode.usingEraser = True
        if ((mode.width-mode.width/10 > x > mode.width-1.5*mode.width/10) and
           (60 > y > 0)):
           mode.toolFill = 'Yellow'
           NoteBookMode.turnEverythingOff(mode)
           mode.currentlyDrawing = True
        if ((mode.width-1.5*mode.width/10 > x > mode.width-2*mode.width/10) and
           (60 > y > 0)):
           mode.toolFill = 'Black'
           NoteBookMode.turnEverythingOff(mode)
           mode.currentlyDrawing = True
        # flip through pages for speech notes
        if ((2*mode.width/20 < x < 3*mode.width/20) and 
           (mode.height > y > mode.height-60)):
           if mode.onSpeechPage < len(mode.speechNotes)-1:
               mode.onSpeechPage += 1
        if ((0 < x < mode.width/20) and (mode.height > y > mode.height-60) and
           (mode.onSpeechPage != 0)):
           mode.onSpeechPage -= 1
        # opens the on screen keyboard
        if ((3*mode.width/20 < x < 5*mode.width/20) and 
           (mode.height > y > mode.height-60)):
            NoteBookMode.keyboard(mode)
        # flip through pages for the notebook
        if ((mode.width-4.5*mode.width/10 > x > mode.width-5*mode.width/10) and
           (60 > y > 0)):
           mode.selectedCorners = [(None, None), (None, None)]
           mode.onPage += 1
           # adds new lists for page drawings and images to keep up with pages
           mode.drawingTuples.append([])
           mode.images.append([])
           mode.tables.append([])
           mode.typedText.append([[None]*56 for i in range(21)])
           mode.onCharacter = [0, 0]
           mode.typos = {}
           #NoteBookMode.turnEverythingOff(mode)
        if ((mode.width-5.5*mode.width/10 > x > mode.width-6*mode.width/10) and
           (60 > y > 0)) and mode.onPage != 0:
           mode.selectedCorners = [(None, None), (None, None)]
           mode.onPage -= 1
           mode.onCharacter = [0, 0]
           mode.typos = {}
        # selecting text on and off
        if ((mode.width-3*mode.width/10 > x > mode.width-3.5*mode.width/10) and
           (0 < y < 60)):
           mode.selectingText = not mode.selectingText 
           mode.displayTypos = False
           mode.typos = {}
           return
        # write and save a csv file of the notes
        if ((mode.width-4*mode.width/10 > x > mode.width-4.5*mode.width/10) and
           (60 > y > 0)):
           mode.currentlyDrawing = False
           mode.usingEraser = False
           nameFile = mode.getUserInput('Enter a name for your saved file.')
           saveFile(nameFile, mode.typedText, mode.drawingTuples, 
                    mode.speechNotes, mode.images, mode.tables)
           return
        # opens a csv file saved and written for LiveNotes  
        if ((mode.width-3.5*mode.width/10 > x > mode.width-4*mode.width/10) and
           (60 > y > 0)):
           # learned how to use askopenfilename() from: 
           # https://stackoverflow.com/questions/3579568            
           filename = askopenfilename()
           filename = filename.split('/')
           filename = filename[-1]
           if filename[-4:] != '.csv':
               return
           mode.onPage = 0
           mode.onSpeechPage = 0
           # updates data structures to essentially open a file
           typedText,drawingTuples,speechNotes,images,tables=openFile(filename)
           mode.typedText = typedText
           mode.drawingTuples = drawingTuples
           mode.speechNotes = speechNotes
           # cleans speech notes which are altered when saved to a csv file
           for i in range(len(mode.speechNotes)):
               if mode.speechNotes[i] == ['""']:
                    mode.speechNotes[i] = ['']
           mode.images = images
           # scales images to the size they were saved at
           for i in range(len(mode.images)):
               for j in range(len(mode.images[i])):
                   reOpenImage=mode.images[i][j][4]
                   mode.currentImage=mode.loadImage(reOpenImage)
                   divisor=(mode.images[i][j][1][1]-mode.images[i][j][0][1])*12
                   scale=1/(mode.currentImage.size[0]/divisor)
                   reOpenImage=mode.scaleImage(mode.currentImage, scale)
                   mode.images[i][j][2]=reOpenImage
           # updates the serial numbers so tags do not start at 0 if there
           # were images or tables in the opened file
           highestSerialNum = ' image0'
           for images in mode.images:
               if images == []:
                   continue
               for image in images:
                   if image[3] > highestSerialNum:
                       highestSerialNum = image[3]
           mode.imageSerialNum = int(highestSerialNum[6:])+1
           # updates tables and finds their current serial number
           mode.tables = tables
           highestSerialNum2 = ' ■table0'
           for tables in mode.tables:
               if tables == []:
                   continue
               for table in tables:
                   if table[1] > highestSerialNum2:
                       highestSerialNum2 = table[1]
           mode.tableSerialNum = int(highestSerialNum2[7:])+1
           return
    # accounts for mouse dragging for events like drawing/erasing and text
    # selection and image resizing/moving
    def mouseDragged(mode, event):
        # this row, col tuple is not the cursor; it is the location of the mouse
        (row, col)=textCorners(event.x, event.y, mode.width, 
                               mode.typedText[mode.onPage])
        # tracks direction mouse is being dragged for reference in image actions 
        mode.visitedCoords[1] = mode.visitedCoords[0]
        mode.visitedCoords[0] = [row, col]
        if None not in mode.visitedCoords:
            if [None, None] not in mode.visitedCoords:
                if mode.visitedCoords[0][0] < mode.visitedCoords[1][0]:
                    mode.direction[0] = 'Up'
                if mode.visitedCoords[0][0] > mode.visitedCoords[1][0]:
                    mode.direction[0] = 'Down'
                if mode.visitedCoords[0][1] > mode.visitedCoords[1][1]:
                    mode.direction[1] = 'Right'
                if mode.visitedCoords[0][1] < mode.visitedCoords[1][1]:
                    mode.direction[1] = 'Left'
        # determines the text representation of the image acted on
        imageTag = None
        if ((row, col) != (None, None) and mode.editImage != None and 
            mode.images[mode.onPage] != []):
            imageTag = mode.images[mode.onPage][mode.editImage][3]
        # resizes the image
        if ((mode.selectingText) and (mode.imageAction == 'resizing') and 
            (not (row, col) == (None, None)) and (not row>20 and not col>55) and
            mode.editImage != None):
            imageData = mode.images[mode.onPage][mode.editImage]
            # make sure the image doesn't end up being sized too small
            if (([row, col] > mode.images[mode.onPage][mode.editImage][0]) and
                (row-3 > mode.images[mode.onPage][mode.editImage][0][0]) and
                (col-3 > mode.images[mode.onPage][mode.editImage][0][1])):
                # clears previous image text representation as image moves
                cleanImageText(imageData, mode.typedText[mode.onPage])
                # notebook dimensions of image
                topLeft = imageData[0]
                bottomRight = imageData[1]
                leftCol = topLeft[1]
                rightCol = bottomRight[1]
                # scale image properly as it is being resized
                divisor = (rightCol-leftCol)*12
                if divisor > 0:
                    scale = 1/(mode.currentImage.size[0]/divisor)   
                    scaledImage0 =  mode.scaleImage(mode.currentImage, scale)
                    mode.images[mode.onPage][mode.editImage][2] = scaledImage0
                    height = imageData[2].size[1]//30 + 1
                    top = imageData[0][0]
                    left = imageData[0][1]
                    # prevents image from getting out of page bounds
                    if top+height > 21:
                        while top+height > 21:
                            divisor -= 12
                            scale = 1/(mode.currentImage.size[0]/divisor)
                            sImage = mode.scaleImage(mode.currentImage, scale)
                            mode.images[mode.onPage][mode.editImage][2] = sImage
                            height = imageData[2].size[1]//30 + 1
                        # also adjust width to reduced height
                        col = left+divisor/12
                    # determines if image resizing will interfere with other 
                    # text/images
                    testImageData = imageData[:]
                    testImageData[1] = [top+height, int(col)]
                    if not legalImageMovement(testImageData, 
                                              mode.typedText[mode.onPage]):
                        # reduces illegal height change to prevent text overlap
                        divisor -= 12
                        scale = 1/(mode.currentImage.size[0]/divisor)
                        scaledImage = mode.scaleImage(mode.currentImage, scale)
                        mode.images[mode.onPage][mode.editImage][2]=scaledImage
                        imageOnText(imageData, mode.typedText[mode.onPage])
                        # shifts text down (if possible)
                        lowestBlank=lowestBlankRow(mode.typedText[mode.onPage])
                        if lowestBlank != None and lowestBlank > top+height:
                            push = imageData[1][0]
                            mode.typedText[mode.onPage].pop(lowestBlank)
                            mode.typedText[mode.onPage].insert(push, [None]*56)
                            moveImagesDown(mode.typedText[mode.onPage], 
                                           mode.images[mode.onPage], row, 
                                           lowestBlank, False, 
                                           mode.tables[mode.onPage])
                            return
                        return
                    # checks if a resize is legal
                    secondTest = mode.images[mode.onPage][mode.editImage]
                    secondTest[1] = [top+height, int(col)]
                    if legalImageMovement(secondTest, 
                                          mode.typedText[mode.onPage]):
                        # resizes the image text representation and image itself
                        bottomL = [top+height, int(col)]
                        mode.images[mode.onPage][mode.editImage][1] = bottomL
                        imageOnText(imageData, mode.typedText[mode.onPage])
            return
        # moves an image
        if ((mode.selectingText) and (mode.imageAction == 'moving') and 
            (not (row, col) == (None, None)) and (imageTag != None) and
            (mode.typedText[mode.onPage][row][col]==imageTag) and
            mode.editImage != None):
            # save data structures to perform tests on while others are edited
            imageData = mode.images[mode.onPage][mode.editImage]
            originalImageData = imageData[:]
            testOriginalImageData = originalImageData[:]
            # referenced for legal move tests
            highestBlank = highestBlankRow(mode.typedText[mode.onPage])
            lowestBlank = lowestBlankRow(mode.typedText[mode.onPage])
            topLeft = imageData[0]
            bottomRight = imageData[1]
            top = topLeft[0]
            bottom = bottomRight[0]
            height = bottomRight[0]-topLeft[0]
            width = bottomRight[1]-topLeft[1]
            halfHeight = height//2
            halfWidth = width//2
            # helps determine a spot to move the image
            imageCenter = textCorners(event.x, event.y, mode.width, 
                                      mode.typedText[mode.onPage])
            newTopLeft = [imageCenter[0]-halfHeight, imageCenter[1]-halfWidth]
            newBottomRight = [newTopLeft[0]+height, newTopLeft[1]+width]
            if ((newTopLeft[0] < 0 or newTopLeft[1] < 0) or
                (newBottomRight[0] > 20 or newBottomRight[1] > 55)):
                return
            # discounts vertical direction changes for illegal moves since text
            # is only moved up and down
            testImageData = imageData[:]
            testTopLeft = newTopLeft[:]
            testBottomRight = newBottomRight[:]
            testTopLeft[1] = testOriginalImageData[0][1]
            testBottomRight[1] = testOriginalImageData[1][1]
            testImageData[0] = testTopLeft
            testImageData[1] = testBottomRight
            if not legalImageMovement(testImageData, 
                                      mode.typedText[mode.onPage]):
                if ((mode.direction[0] == 'Up') and (highestBlank != None) and
                    (imageCenter[0] < lowestBlank)):
                    if highestBlank < imageData[0][0]:
                        mode.typedText[mode.onPage].pop(highestBlank)
                        mode.typedText[mode.onPage].insert(top, [None]*56)
                        newTopLeft = topLeft[:]
                        newTopLeft[0] -= 1
                        newBottomRight = bottomRight[:]
                        newBottomRight[0] -= 1
                        newBottomR = newBottomRight
                        mode.images[mode.onPage][mode.editImage][0]=newTopLeft
                        mode.images[mode.onPage][mode.editImage][1]=newBottomR
                        imageData = mode.images[mode.onPage][mode.editImage]
                        cleanImageText(originalImageData, 
                                       mode.typedText[mode.onPage])
                        imageOnText(imageData, mode.typedText[mode.onPage])
                        # frees up space for image to move
                        for imageData in mode.images[mode.onPage]:
                            cleanAllImageText(imageData, 
                                              mode.typedText[mode.onPage])
                        # move other images accordingly
                        moveImagesUp(mode.typedText[mode.onPage], 
                                     mode.images[mode.onPage], highestBlank, 
                                     row, False, mode.tables[mode.onPage])
                        # cleans and replaces image text
                        resetImagesTables(mode.typedText[mode.onPage], 
                                          mode.images[mode.onPage], 
                                          mode.tables[mode.onPage])
                    return
                if ((mode.direction[0] == 'Down') and (lowestBlank != None) and
                    (imageCenter[0] > highestBlank)):
                    if ((lowestBlank > imageData[1][0])):
                        mode.typedText[mode.onPage].pop(lowestBlank)
                        mode.typedText[mode.onPage].insert(bottom, [None]*56)
                        newTopLeft = topLeft[:]
                        newTopLeft[0] += 1
                        newBottomRight = bottomRight[:]
                        newBottomRight[0] += 1
                        newBottomR = newBottomRight
                        mode.images[mode.onPage][mode.editImage][0]=newTopLeft
                        mode.images[mode.onPage][mode.editImage][1]=newBottomR
                        imageData = mode.images[mode.onPage][mode.editImage]
                        cleanImageText(originalImageData, 
                                       mode.typedText[mode.onPage])
                        # moves other images accordingly
                        moveImagesDown(mode.typedText[mode.onPage], 
                                       mode.images[mode.onPage], row, 
                                       lowestBlank, False, 
                                       mode.tables[mode.onPage])
                        imageOnText(imageData, mode.typedText[mode.onPage])
                    return
            # prevents image from collapsing other text and images
            testImageData2 = imageData[:]
            testImageData2[0] = newTopLeft
            testImageData2[1] = newBottomRight
            if not legalImageMovement(testImageData2, 
                                      mode.typedText[mode.onPage]):
                return
            # legal image movement without altering other text and iamges
            mode.images[mode.onPage][mode.editImage][0] = newTopLeft
            mode.images[mode.onPage][mode.editImage][1] = newBottomRight
            imageData = mode.images[mode.onPage][mode.editImage]
            cleanImageText(originalImageData, mode.typedText[mode.onPage])
            imageOnText(imageData, mode.typedText[mode.onPage])
            return
        if mode.selectingText:
            mode.selectedCorners[1] = (row, col)
            # moves cursor as text is being selected
            if (None, None) not in mode.selectedCorners:
                (row, col) = min(mode.selectedCorners)
                if mode.selectedCorners[0] > mode.selectedCorners[1]:
                    # adjusts/fits  text selection when moving selection upwards
                    mode.onCharacter[0] = row 
                    mode.onCharacter[1] = col
                else:
                    (row, col) = max(mode.selectedCorners)
                    mode.onCharacter[0] = row
                    mode.onCharacter[1] = col
            return
        # returns if events do not fall in bounds of notebook 
        if event.x < mode.width/2.5:
            return
        if event.y < 60:
            return
        # erases drawings emptying their tuple line coordinate representations
        if mode.usingEraser:
            mode.eraser = (event.x, event.y)
            for i in range(len(mode.drawingTuples[mode.onPage])):
                x = mode.drawingTuples[mode.onPage][i][0]
                y = mode.drawingTuples[mode.onPage][i][1]
                if inEraserBounds(x, y, mode.eraser, mode.lineWidth):
                    mode.drawingTuples[mode.onPage][i]=(None, None, None, None)
        # appends coordinates to drawing data structures to create lines that
        # form drawings
        elif mode.currentlyDrawing:
            mode.drawingTuples[mode.onPage].append((event.x, event.y, 
                                                mode.lineWidth, mode.toolFill))
            if len(mode.drawingTuples[mode.onPage]) < 2:
                return
            (x, y) = mode.drawingTuples[mode.onPage][-2][:2] 
            (x2, y2) = (event.x, event.y)
            if not (((x, y) == (None, None) or (x2, y2) == (None, None))):
                lineDistance = ((x2-x)**2 + (y2-y)**2)**0.5
                if (x2-x) == 0:
                    lineSlope = None
                else:
                    lineSlope = (y2-y)/(x2-x)
                # divides longer lines into smaller lines for smoother erasing
                if lineDistance >= 25:
                    lineChops = int(lineDistance/12.5)
                    xDistance = x2-x
                    yDistance = y2-y
                    xChop = xDistance/lineChops
                    yChop = yDistance/lineChops
                    for i in range(1, lineChops):
                        newX = x + i*xChop
                        newY = y + i*yChop
                        tupBetween = (newX, newY, mode.lineWidth, mode.toolFill)
                        mode.drawingTuples[mode.onPage].insert(-1, tupBetween)

    # accounts for mouse releasing events like drawing (ending a line)
    def mouseReleased(mode, event):
        mode.drawingTuples[mode.onPage].append((None, None, None, None))

    # accounts for all keyboard events (typing onto the notebook)
    def keyPressed(mode, event):
        # differentiate between online keyboard and real keyboard entries
        if isinstance(event, str):
            eventKey = event
            if mode.capsLock and len(eventKey)==1:
                eventKey = eventKey.upper()
        else:
            eventKey = event.key
        # useful resets for when columns or table editing goes out of bounds
        if mode.onCharacter[1] > 56: mode.onCharacter[1] = 56
        (row, col) = (mode.onCharacter[0], mode.onCharacter[1])
        mode.editImage = None
        mode.editTable = None    
        # convert event keys to their appropriate character
        if eventKey == 'Space':
            if row == 20 and col == 56:
                return
            eventKey = ' '
        if eventKey == 'Tab':
            eventKey = ' '   
        # return to home screen             
        if eventKey == 'Escape':
            mode.app.setActiveMode(mode.app.splashScreenMode)                   
            return
        # updates typo finding as text is shifted around with such keys
        if (mode.displayTypos and 
            eventKey in {' ', 'Delete', 'Up', 'Down', 'Left', 'Right'} and 
            not col==56):
            mode.typos = findTypos(mode.typedText[mode.onPage])
        # creates pi symbol after spacing away from 'pi' spelling
        if mode.math and eventKey==' ' and not mode.typingInTable:
            findPi(mode.typedText[mode.onPage], row)
            findRoot(mode.typedText[mode.onPage], row)
            findAprx(mode.typedText[mode.onPage], row)
        # enables creating exponent characters upon using '^'
        if mode.math and eventKey=='^':
            mode.powerOf=True
        # determines end of writing an exponent
        if mode.math and mode.powerOf and eventKey==' ':
            powers(mode.typedText[mode.onPage], row)
            mode.powerOf=False
        # typing system for table cells
        if mode.typingInTable:
            onRow = mode.onTableRowCol[0]
            onCol = mode.onTableRowCol[1]
            table = mode.tables[mode.onPage][mode.onTable]
            colWidth = 56 // (len(table[0][0])-2)
            # allows arrow key use
            cursor = mode.onCellIndex
            if eventKey == 'Left' and mode.onCellIndex > 0:
                mode.onCellIndex -= 1
                if cursor > 0: cursor -= 1
            if (eventKey == 'Right' and 
                mode.onCellIndex < len(table[0][onRow][onCol])):
                mode.onCellIndex += 1
                cursor += 1
            if not eventKey == 'Delete' and len(eventKey) == 1:
                location=mode.tables[mode.onPage][mode.onTable][0][onRow][onCol]
                location.insert(cursor, eventKey)
                mode.onCellIndex += 1
                cursor += 1
            elif (eventKey == 'Delete' and 
                  mode.tables[mode.onPage][mode.onTable][0][onRow][onCol]!=[]):
                dlt = cursor-1
                mode.tables[mode.onPage][mode.onTable][0][onRow][onCol].pop(dlt)
                if mode.onCellIndex > 0:
                    mode.onCellIndex -= 1
                    cursor -= 1
            # determines where to draw the cursor as a cell is typed in
            cursorRow = table[0][onRow][0][0] + cursor // colWidth
            # uses real colWidth
            cursorR = int(cursor%colWidth)*12
            cursorCol=(onCol-1)*(56/(len(table[0][0])-2)*12)+cursorR
            mode.cursorRowAndCol = [cursorRow, cursorCol]
            currRow = mode.tables[mode.onPage][mode.onTable][0][onRow]
            currCol = currRow[onCol]
            colHeight = currRow[-1][0]-currRow[0][0]
            # makes a cell taller if the text is too long to fit 
            if len(currCol) > colWidth*colHeight:
                lowestBlank = lowestBlankRow(mode.typedText[mode.onPage])
                bottom = mode.tables[mode.onPage][mode.onTable][0][-1][-1][0]
                # makes sure stretching the cell is legal
                if (bottom <= lowestBlank):
                    # moves text below the expanding cell down 
                    if not mode.typedText[mode.onPage][bottom]==[None]*56:
                        mode.typedText[mode.onPage].pop(lowestBlank)
                        mode.typedText[mode.onPage].insert(bottom, [None]*56)
                    stretchTable(mode.tables[mode.onPage][mode.onTable][0],
                                 onRow)
                    tableOnText(mode.typedText[mode.onPage], table)
                    moveImagesDown(mode.typedText[mode.onPage], 
                                   mode.images[mode.onPage], bottom, 
                                   lowestBlank, False, mode.tables[mode.onPage])
                    resetImagesTables(mode.typedText[mode.onPage],
                                      mode.images[mode.onPage],
                                      mode.tables[mode.onPage])
                # undoes illegal cell stretching
                else:
                    c=mode.tables[mode.onPage][mode.onTable][0][onRow][onCol]
                    c=c[:-1]
                    mode.tables[mode.onPage][mode.onTable][0][onRow][onCol]=c
                    mode.onCellIndex -= 1
            return
        #copies text
        if ((eventKey == 'c') and (mode.selectingText) and
            (not (None, None) in mode.selectedCorners)):
            # accounts for dragging the mouse left and upwards, ensures
            # the upper and lower corner are in the right list indexes
            if ((mode.selectedCorners[0][0] > mode.selectedCorners[1][0]) or 
                (mode.selectedCorners[0][1] > mode.selectedCorners[1][1])):
                mode.selectedCorners = mode.selectedCorners[::-1]
            # creates block of copied text
            top = mode.selectedCorners[0][0]
            bottom = mode.selectedCorners[1][0]
            left = mode.selectedCorners[0][1]
            right = mode.selectedCorners[1][1]
            copiedTextBlock = []
            for i in range(top, bottom+1):
                row = []
                for j in range(left, right):
                    if mode.typedText[mode.onPage][i][j] == None:
                        row.append(None)
                        continue
                    # do not copy and paste images or fractions of images
                    if ('image' in mode.typedText[mode.onPage][i][j] or 
                        'table' in mode.typedText[mode.onPage][i][j]): 
                        row.append(None)
                        continue
                    if mode.typedText[mode.onPage][i][j][0] == ' ':
                        row.append(None)
                    else:
                        row.append(mode.typedText[mode.onPage][i][j])
                copiedTextBlock.append(row)
            # clean blank edges off text block
            mode.copiedText = trimTextBlock(copiedTextBlock)
            mode.selectedCorners = [(None, None), (None, None)]
            return
        # pastes text
        if ((eventKey == 'v') and (mode.selectingText) and 
            (mode.selectedCorners == [(None, None), (None, None)])):
            if not isLegalPaste(row, col, mode.copiedText, 
                                mode.typedText[mode.onPage]):
                return
            # shift rows down for a paste
            rowsToPop = len(mode.copiedText)-1
            while rowsToPop != 0:
                rowsToPop -= 1
                # shifts images down as pasted text shifts the page
                lowestBlank = lowestBlankRow(mode.typedText[mode.onPage])
                moveImagesDown(mode.typedText[mode.onPage], 
                               mode.images[mode.onPage], row, lowestBlank, 
                               False, mode.tables[mode.onPage])
                blankRow = mode.typedText[mode.onPage].pop(lowestBlank)
                mode.typedText[mode.onPage].insert(row+1, blankRow)
                resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
            # clean former text representations off before creating new ones
            resetImagesTables(mode.typedText[mode.onPage], 
                              mode.images[mode.onPage], 
                              mode.tables[mode.onPage])
            pasteRow = 0
            for r in range(row, row+len(mode.copiedText)):
                pasteCol = 0
                for c in range(col, col+len(mode.copiedText[0])):
                    copiedTxt = mode.copiedText[pasteRow][pasteCol]
                    mode.typedText[mode.onPage][r][c] = copiedTxt
                    pasteCol += 1
                pasteRow += 1
            return
        if ((eventKey == 'Delete') and (mode.selectingText) and
            (not (None, None) in mode.selectedCorners)):
            # accounts for dragging the mouse left and upwards, ensures
            # the upper and lower corner are in the right place
            if ((mode.selectedCorners[0][0] > mode.selectedCorners[1][0]) or 
                (mode.selectedCorners[0][1] > mode.selectedCorners[1][1])):
                mode.selectedCorners = mode.selectedCorners[::-1]
            top = mode.selectedCorners[0][0]
            bottom = mode.selectedCorners[1][0]
            left = mode.selectedCorners[0][1]
            right = mode.selectedCorners[1][1]
            deletedTextBlock = []
            for i in range(top, bottom+1):
                row = []
                for j in range(left, right):
                    if mode.typedText[mode.onPage][i][j] == None:
                        row.append(None)
                        continue
                    if ('image' in mode.typedText[mode.onPage][i][j] or 
                        'table' in mode.typedText[mode.onPage][i][j]):
                        row.append(None)
                        continue
                    if mode.typedText[mode.onPage][i][j][0] == ' ':
                        row.append(None)
                    else:
                        row.append(mode.typedText[mode.onPage][i][j])
                deletedTextBlock.append(row)
            mode.copiedText = trimTextBlock(deletedTextBlock)
            # determines selected images to be deleted and deletes them and 
            # their text representations
            deleteTags = set()
            for row in range(mode.selectedCorners[0][0], 
                             mode.selectedCorners[1][0]+1):
                for col in range(mode.selectedCorners[0][1], 
                                 mode.selectedCorners[1][1]):
                    if ((mode.typedText[mode.onPage][row][col] != None) and
                        ('image' in mode.typedText[mode.onPage][row][col])):
                        deleteTags.add(mode.typedText[mode.onPage][row][col])
            for tag in deleteTags:
                for row in range(21):
                    for col in range(56):
                        if mode.typedText[mode.onPage][row][col] == tag:
                            mode.typedText[mode.onPage][row][col] = None
            deleteImages = []
            for tag in deleteTags:
                for img in mode.images[mode.onPage]:
                    if tag in img:
                        deleteImages.append(mode.images[mode.onPage].index(img))
            # pop images in backwards order to not accidentally pop earlier
            # images
            deleteImages = sorted(deleteImages)[::-1]
            for imgIndex in deleteImages:
                mode.images[mode.onPage].pop(imgIndex)
            page = changeText(mode.selectedCorners, mode.typedText[mode.onPage],
                              'Delete')
            mode.typedText[mode.onPage] = page
            mode.selectedCorners = [(None, None), (None, None)]
            return
        if eventKey[1:2] == ' ' or len(eventKey) == 1:
            if mode.bold:
                eventKey += ' b'
            if mode.italic:
                eventKey += ' i'
            (row, col) = (mode.onCharacter[0], mode.onCharacter[1])
            if (mode.underline and not mode.overstrike and 
                not mode.onCharacter[1] == 56):
                eventKey += ' u1'
            if (mode.overstrike and not mode.underline and 
                not mode.onCharacter[1] == 56):
                eventKey += ' o1'
            if (mode.underline and mode.overstrike and 
                not mode.onCharacter[1] == 56):
                eventKey += ' uo'
        # removes loose ' ' characters at the end of rows
        for rowI in range(len(mode.typedText[mode.onPage])):
            for colI in range(len(mode.typedText[mode.onPage][rowI])):
                if ((mode.typedText[mode.onPage][rowI][colI] != ' ') or
                   (mode.typedText[mode.onPage][rowI][colI] != None)):
                   break
                elif mode.typedText[mode.onPage][rowI][colI] == ' ':
                    mode.typedText[mode.onPage][rowI][colI] = None
        #clears ' ' spaces out of empty rows
        for i in range(len(mode.typedText[mode.onPage])):
            uniqueChars = set()
            for char in mode.typedText[mode.onPage][i]:
                uniqueChars.add(char)
                if (' ' in uniqueChars and None in uniqueChars and 
                    len(uniqueChars) == 2):
                    mode.typedText[mode.onPage][i] = [None]*56
        # determines the closest tail column to the cursor in a row above 
        blankColAbove = None
        while blankColAbove == None:
            if row == 0: 
                break
            if mode.typedText[mode.onPage][row-1] == [None]*56:
                blankColAbove = 0
                break
            if ((mode.typedText[mode.onPage][row-1][55] != ' ') and
                (mode.typedText[mode.onPage][row-1][55] != None)):
                break
            for colI in range(55, 0, -1):
                if ((mode.typedText[mode.onPage][row-1][colI] != ' ') and
                    (mode.typedText[mode.onPage][row-1][colI] != None)):
                    blankColAbove = colI+1
                    if blankColAbove == 56:
                        blankColAbove = None
                    break
            break
        # determines the closest blank row below the cursor (if any)
        blankRowBelow = None
        while blankRowBelow == None:
            for rowI in range(row+1, 20):
                if mode.typedText[mode.onPage][rowI] == [None]*56:
                    blankRowBelow = rowI
                    break
            break
        # deletes text from 2D list of text
        if eventKey == 'Delete':
            # shift up a row
            if col == 0:
                # moves images up too
                if (mode.images[mode.onPage] != [] or 
                    mode.tables[mode.onPage] != []):
                    highestBlank = highestBlankRow(mode.typedText[mode.onPage])
                    # move other images accordingly
                    moveImagesUp(mode.typedText[mode.onPage], 
                                 mode.images[mode.onPage], highestBlank, row, 
                                 True, mode.tables[mode.onPage])
                    # cleans and replaces image text
                # moves text below cursor upward if there is space 
                if mode.typedText[mode.onPage][row-1] == [None]*56:
                    mode.typedText[mode.onPage].pop(row-1)
                    mode.typedText[mode.onPage].append([None]*56)
                    if not row == 0:
                        mode.onCharacter[0] -= 1
                        mode.onCharacter[1] = blankColAbove
                    #return
                # shifts text below cursor up by popping the blank row a cursor 
                # was on and inserting a new blank one below everything
                elif mode.typedText[mode.onPage][row] == [None]*56:
                    mode.typedText[mode.onPage].pop(row)
                    mode.typedText[mode.onPage].append([None]*56)
                    if not row == 0:
                        mode.onCharacter[0] -= 1
                    if not blankColAbove == None:
                        mode.onCharacter[1] = blankColAbove
                    else:
                        mode.onCharacter[1] = 56
                    #return
                resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
                return
            # moves cursor up to the end column of the above row
            if col == 0 and row != 0:
                mode.onCharacter[0] -= 1
                mode.onCharacter[1] = 56
                return
            # deletes text character from a 2D list and shifts backward 
            if col != 0:
                mode.onCharacter[1] -= 1
                # deletes an entire image if delete hits the side of one
                if ((mode.typedText[mode.onPage][row][col-1] != None) and
                    ('image' in mode.typedText[mode.onPage][row][col-1])):
                    imageTag = mode.typedText[mode.onPage][row][col-1]
                    for row in range(21):
                        for col in range(56):
                            if mode.typedText[mode.onPage][row][col]==imageTag:
                                mode.typedText[mode.onPage][row][col] = None
                    for img in mode.images[mode.onPage]:
                        if imageTag in img:
                            imgIndex = mode.images[mode.onPage].index(img)
                    mode.images[mode.onPage].pop(imgIndex)
            # deletes a character
            mode.typedText[mode.onPage][row][col-1] = 'Del'
            mode.typedText[mode.onPage][row].remove('Del')
            mode.typedText[mode.onPage][row].append(None)
            # prevents keys from interfering with image text representation by
            # resetting them when they are shifted out of place (erases and
            # recreates them based on their corners)
            resetImagesTables(mode.typedText[mode.onPage], 
                              mode.images[mode.onPage], 
                              mode.tables[mode.onPage])
            return
        # determines the lowest blank row (if any), used as reference to shift
        # down rows upon pressing enter
        lowestBlank = lowestBlankRow(mode.typedText[mode.onPage])
        if eventKey == 'Enter':
            # seperate circumstances for images (so that images cannot get
            # split in half)
            if mode.images[mode.onPage] != [] or mode.tables[mode.onPage] != []:
                if mode.onCharacter[0] == 20:
                    return
                if lowestBlank == 0:
                    return
                if lowestBlank < row:
                    if mode.onCharacter[1] < 20:
                        mode.onCharacter[0] += 1
                    return
                if (mode.bulleting and 
                    not imageInRow(mode.typedText[mode.onPage], row)):
                    mode.typedText[mode.onPage].pop(lowestBlank)
                    bulletedRow = [None]*5 + ['●'] + [None]*50
                    mode.typedText[mode.onPage].insert(row+1, bulletedRow)
                    mode.onCharacter[0] += 1
                    mode.onCharacter[1] = 7
                if not mode.bulleting:
                    if col == 0:
                        blankRow = mode.typedText[mode.onPage].pop(lowestBlank)
                        currRow = mode.typedText[mode.onPage][row]
                        mode.typedText[mode.onPage].insert(row, blankRow)
                        mode.typedText[mode.onPage][row+1] = currRow
                    # entering midline while there are images does not split
                    # the line in half so as to avoid damaging images
                    else:
                        blankRow = mode.typedText[mode.onPage].pop(lowestBlank)
                        mode.typedText[mode.onPage].insert(row+1, blankRow)
                # shift images and tables down if any are below entered row     
                moveImagesDown(mode.typedText[mode.onPage], 
                               mode.images[mode.onPage], row, lowestBlank, 
                               False, mode.tables[mode.onPage])
                if not mode.bulleting:
                    mode.onCharacter[0] += 1
                    mode.onCharacter[1] = 0
            # typical enter circumstances
            elif mode.images[mode.onPage] == []:
                if mode.onCharacter[0] == 20:
                    return
                if lowestBlank == None:
                    return
                if lowestBlank < row:
                    if mode.onCharacter[1] < 20:
                        mode.onCharacter[0] += 1
                    return
                # creates a bulleted list upon entering
                if mode.bulleting:
                    mode.typedText[mode.onPage].pop(lowestBlank)
                    bulletedRow = [None]*5 + ['●'] + [None]*50
                    mode.typedText[mode.onPage].insert(row+1, bulletedRow)
                    mode.onCharacter[0] += 1
                    mode.onCharacter[1] = 7
                    resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
                    return
                blankRow = mode.typedText[mode.onPage].pop(lowestBlank)
                # chops the current row and entered row into appropriate halves
                if mode.onCharacter[1] != 0:
                    insertD=mode.typedText[mode.onPage][row][col:]+[None]*(col)
                    mode.typedText[mode.onPage].insert(row+1, insertD)
                    txt=mode.typedText[mode.onPage][row][:col]+[None]*(56-col)
                    mode.typedText[mode.onPage][row]=txt
                else:
                    currRow = mode.typedText[mode.onPage][row]
                    mode.typedText[mode.onPage].insert(row, blankRow)
                    mode.typedText[mode.onPage][row+1] = currRow
                mode.onCharacter[0] += 1
                mode.onCharacter[1] = 0
            return   
        if eventKey == 'Right':
            if col == 56 and row != 20:
                mode.onCharacter[0] += 1
                mode.onCharacter[1] = 0
                return
            elif col == 56:
                return
            mode.onCharacter[1] += 1
            return
        if eventKey == 'Left':
            if col == 0 and mode.onCharacter[0] != 0:
                mode.onCharacter[0] -= 1
                mode.onCharacter[1] = 56
                return
            elif col == 0:
                return
            mode.onCharacter[1] -= 1
            return
        if eventKey == 'Up':
            if row == 0:
                return
            mode.onCharacter[0] -= 1
            return
        if eventKey == 'Down':
            if row == 20:
                return
            mode.onCharacter[0] += 1
            return
        # finds the farthest blank column in the row to see where cursor goes
        farthestBlankColInRow = None
        while farthestBlankColInRow == None:
            for colI in range(55, -1, -1):
                if mode.typedText[mode.onPage][row][colI] == None:
                    farthestBlankColInRow = colI
                    break
            if farthestBlankColInRow == None and col != 56:
                if mode.typedText[mode.onPage][row][col] == ' ':
                    mode.typedText[mode.onPage][row][col] = eventKey
                    mode.onCharacter[1] += 1
                return
            break
        # returns if the notebook pages boundary has been reached
        if ((mode.onCharacter[0] == 20) and (mode.onCharacter[1] == 55) and
            (mode.typedText[mode.onPage][row][col]) == None):
           mode.typedText[mode.onPage][row][col] = eventKey
           return
        if mode.onCharacter[0] == 20:
            if mode.onCharacter[1] == 56:
                return
            if col < farthestBlankColInRow:
                mode.typedText[mode.onPage][row].pop(farthestBlankColInRow)
                mode.typedText[mode.onPage][row].insert(col, eventKey)
                mode.onCharacter[1] += 1
                # prevents keys from interfering with image text representation
                resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
            return
        # prevents typing off page and crashing
        elif mode.onCharacter[0] == 20 and mode.onCharacter[1] == 56:
            return
        # different processes for typing at the end of the line and 
        # transitioning to the next line
        if mode.onCharacter[1] == 56:
            # shift images and their text representations down
            moveImagesDown(mode.typedText[mode.onPage], 
                           mode.images[mode.onPage], row, lowestBlank, False, 
                           mode.tables[mode.onPage])
            if mode.onCharacter[0] == 20:
                return
            if (not eventKey==None and eventKey[0]==' ' and 
                mode.onCharacter[1] != 20):
                if mode.bulleting:
                    mode.onCharacter[0] += 1
                    mode.onCharacter[1] = 7
                    resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
                    return
                mode.onCharacter[0] += 1
                mode.onCharacter[1] = 0 
            # starts typing a new word on the row below and moves the current
            # typed word down a row so half of it is not left on another row      
            if ((not eventKey==None and eventKey[0] != ' ') and 
                (mode.onCharacter[0] != 20) and
                (mode.typedText[mode.onPage][row][55] in [None, ' ', '']) and
                (lowestBlank != None) and (row < lowestBlank)):
                mode.typedText[mode.onPage].pop(lowestBlank)
                newRow = [eventKey] + [None]*55
                mode.typedText[mode.onPage].insert(row+1, newRow)
                mode.onCharacter[0] += 1
                mode.onCharacter[1] = 1
            # reconstructs the word being typed and moves it to the row below  
            if ((lowestBlank != None) and 
               (mode.typedText[mode.onPage][row][55] != ' ') and
               (eventKey != ' ') and (row < lowestBlank)):
                currentWord = []
                canShiftDown=False
                # checks if a word-in-typing can legally shift down
                for checkI in range(55, 0, -1):
                    if mode.typedText[mode.onPage][row][checkI]==None:
                        canShiftDown=True
                        break
                    elif mode.typedText[mode.onPage][row][checkI][0]==' ':
                        canShiftDown=True
                        break
                if canShiftDown:
                    for charI in range(55, 0, -1):
                        if (mode.typedText[mode.onPage][row][charI] != None and
                            mode.typedText[mode.onPage][row][charI][0] != ' '):
                            wrdAppend = mode.typedText[mode.onPage][row][charI]
                            currentWord.append(wrdAppend)
                            mode.typedText[mode.onPage][row][charI] = None
                        else:
                            break
                # allows 56th character to have an underline/overstrike/both
                if mode.underline and not mode.overstrike:
                    eventKey += ' u1'
                if mode.overstrike and not mode.underline:
                    eventKey += ' o1'
                if mode.underline and mode.overstrike:
                    eventKey += ' uo'
                # places the word being spelled in the row below
                currentWord = currentWord[::-1] + [eventKey]
                mode.typedText[mode.onPage].pop(lowestBlank)
                if mode.bulleting:
                    newRow=[None]*7 + currentWord +[None]*(49-len(currentWord))
                    mode.typedText[mode.onPage].insert(row+1, newRow)
                    mode.onCharacter[0]+=1
                    mode.onCharacter[1]=len(currentWord)+7
                    return
                newRow = currentWord + [None]*(56-len(currentWord))
                mode.typedText[mode.onPage].insert(row+1, newRow)
                mode.onCharacter[0] += 1
                mode.onCharacter[1] = len(currentWord)
                # prevents keys from interfering with image text representation
                resetImagesTables(mode.typedText[mode.onPage], 
                                  mode.images[mode.onPage], 
                                  mode.tables[mode.onPage])
            return  
        # wraps text around images by preventing text from being inside image
        # text representation and also moving a half typed word in its entirety
        # to the side it is being wrapped to
        jumpToCol = None
        currentWord = []
        if col > 55: col=55
        if ((mode.typedText[mode.onPage][row][col] != None) and
            ('image' in mode.typedText[mode.onPage][row][col])):
            jumpToCol = colTextWrap(mode.typedText[mode.onPage], row, col)-1
            if not eventKey == ' ':
                currentWord.append(eventKey)
                for i in range(col-1, -1, -1):
                    if mode.typedText[mode.onPage][row][i] == None:
                        break
                    if mode.typedText[mode.onPage][row][i][0] == ' ':
                        break
                    currentWord.append(mode.typedText[mode.onPage][row][i])
                    mode.typedText[mode.onPage][row][i] = None 
                currentWord = currentWord[::-1]
        # shift cursor to wrap around the image
        if jumpToCol != None and currentWord == []:
            mode.onCharacter[1] = jumpToCol%55
        elif jumpToCol != None:
            mode.onCharacter[1] = jumpToCol+len(currentWord)
            # rewrites current word being wrapped onto the page
            for i in range(len(currentWord)):
                if jumpToCol >= 55:
                    continue
                mode.typedText[mode.onPage][row][jumpToCol] = currentWord[i]
                jumpToCol += 1
        # prevents text character overlap
        rowPop = mode.typedText[mode.onPage][row].pop(farthestBlankColInRow)
        mode.typedText[mode.onPage][row].insert(col, eventKey)
        mode.onCharacter[1] += 1
        if ((mode.onCharacter[1] == 56) and (mode.onCharacter[0] != 20) and 
            (mode.typedText[mode.onPage][row][55] == None)):
            mode.onCharacter[0] += 1
            mode.onCharacter[1] = 0
        if col > farthestBlankColInRow:
            mode.onCharacter[1] -= 1
        # prevents keys from interfering with image text representation
        mode.typedText[mode.onPage]=textTransition(mode.typedText[mode.onPage], 
                                                   mode.images[mode.onPage])
        return

class LiveNotes(ModalApp):
    def appStarted(app):
        app.splashScreenMode = SplashScreenMode()
        app.noteBookMode = NoteBookMode()
        app.helpMode = HelpMode()
        app.setActiveMode(app.splashScreenMode)
app = LiveNotes(width=1200, height=690)