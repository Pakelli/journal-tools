import argparse
import os
import sys
import re
import datetime
import xml.etree.ElementTree as ET
import xml.dom.minidom
from shutil import copytree, copyfile, move

args = None     #command line arguments

def printStatus(text, whenQuiet, textEnd="\n", marker=""):
    toPrint = ""
    if not args.silent and (not args.quiet or whenQuiet):
        toPrint = text
        if marker and not args.nomarker:
            markerText = "[" + marker + "] "
            toPrint = markerText + toPrint
    if toPrint:
        print(toPrint, end=textEnd)

def thisScriptPath():
    '''
    Returns the path of the script
    '''
    return os.path.dirname(os.path.realpath(__file__))

def getYearList(yearStrList):
    #returns every string in yearStrList that is a valid 4-digit number
    newYearList = [];
    for i in yearStrList:
        if len(i) == 4 and i.isdigit():
            newYearList.append(i)
    return newYearList

def isFileAlreadyHere(filename, path):
    '''
    Returns true if any file in "path" has the same file size as "filename".
    '''
    alreadyHere = False

    scriptPath = thisScriptPath()
    fullPath = scriptPath + "/" + path + "/"
    fileSize = os.path.getsize(scriptPath + filename)

    if os.path.isdir(fullPath):
        folderContents = os.listdir(fullPath)
        for f in folderContents:
            if not alreadyHere and os.path.isfile(fullPath + f):
                thisFileSize = os.path.getsize(fullPath + f)
                fileDatetime = datetimeFromFilename(scriptPath + filename)
                thisFileDatetime = datetimeFromFilename(fullPath + f)
                if fileSize == thisFileSize and fileDatetime == thisFileDatetime:
                    alreadyHere = True
    return alreadyHere

def datetimeFromFilename(filenameFull):
    '''
    Attempts to extract time from filename, based on some preset patterns.
    '''
    found = False
    thisDatetime = None
    filename = os.path.splitext(filenameFull)[0]
    match = re.search(r"([0-3]?\d).([0-1]?\d).(\d\d) ([0-1]?\d).([0-5]\d)(am|pm)", filename)
    if match:
        found = True
        thisDatetime = datetime.datetime.strptime(match.group(0), "%d.%m.%y %I.%M%p")
    formats = [
        "VID%Y%m%d%H%M%S",
        "%Y_%m_%d_%H_%M_%S",
        "%j Y-%m-%d %H-%M-%S",
        "%J Y_%m_%d_%H_%M_%S",
        "%j Y_%m_%d_%H_%M_%S",
        "%d.%m.%y %I.%M%p",
        "%Y%m%d%H%M%S",
        "%Y-%m-%d %H-%M-%S"
    ]
    for f in formats:
        if not found:
            try:
                thisDatetime = datetime.datetime.strptime(filename, f)
                found = True
            except ValueError:
                pass
    return thisDatetime

def relocateFile(oldDir, newDir, filename):
    '''
    Either moves or copies (based on shouldMove) file from newDir to oldDir. 
    Also creates newDir if it doesn't exist.
    '''
    oldDirFull = thisScriptPath() + "/" + oldDir
    newDirFull = thisScriptPath() + "/" + newDir
    if not os.path.exists(newDirFull):
        printStatus("Directory /" + newDir + " doesn't exist, creating it... ", False, " ", "NewDir")
        os.makedirs(newDirFull)
        printStatus("done!", False)
    if args.move:
        printStatus("Moving file " + filename + "...", False, " ", " Move ")
        move(oldDirFull + "/" + filename, newDirFull + "/" + filename)
    else:
        printStatus("Copying file " + filename + "...", False, " ", " Copy ")
        copyfile(oldDirFull + "/" + filename, newDirFull + "/" + filename)
    printStatus("done!", False)

def renameFile(dir, filename, filenameNew):
    '''
    Attempts to rename filename to filenameNew
    '''
    dirFull = thisScriptPath() + "/" + dir
    if not os.path.exists(dirFull):
        printStatus("Directory /" + dir + " doesn't exist, creating it... ", False, " ", "NewDir")
        os.makedirs(dirFull)
        printStatus("done!", False)
    printStatus("Renaming file " + filename + "...", False, " ", "Rename")
    move(dirFull + "/" + filename, dirFull + "/" + filenameNew)
    printStatus("done!", False)

def getOrderedFiles(files):
    '''
    Sorts the contents of the list "files" based on the datetime in each entry. 
    Datetime is figured out with datetimeFromFilename()
    '''
    dictFiles = dict()
    for i in files:  #sorting files in filePath based on time
        fileTime = None
        thisDatetime = datetimeFromFilename(i)
        if thisDatetime:
            dictFiles[i] = thisDatetime
        else:
            printStatus(i + " isn't a valid journal file, can't it sort by time.", False, marker="NoSort")
    sortedList = sorted(dictFiles, key=dictFiles.get)
    return sortedList

def getSortedFilename(count, filename):
    '''
    
    '''
    filenameNew = str(count) + " - "
    fileTime = datetimeFromFilename(filename)
    extension = os.path.splitext(filename)[1]
    filenameNew += fileTime.strftime("%d.%m.%y %I.%M%p").lower() + extension
    if count < 10:
        filenameNew = "0" + filenameNew
    return filenameNew

def formatNewFiles(orderedFiles, path):
    '''
    Renames all files in orderedFiles to their sorted filename. 
    Sorted filename comes from getSortedFilename()
    '''
    count = 0
    for f in orderedFiles:
        count += 1
        filenameNew = ""
        match = re.search(r"^([0-3]?\d).([0-1]?\d).(\d\d) ([0-1]?\d).([0-5]\d)(am|pm)", f)
        filenameNew = getSortedFilename(count, f)
        renameFile(path, f, filenameNew)

def sortTimeRecurse(path):
    '''
    Runs through all files in "path" and renames them based on the file time
    that is retrieved through its name. 
    Also calls itself on all folders in path. 
    Returns the amount of files sorted.  
    '''
    count = 0
    fullPath = thisScriptPath() + "/" + path + "/"
    folderContents = os.listdir(fullPath)
    fileList = []
    for f in folderContents:
        if os.path.isdir(fullPath + f):
            count += sortTimeRecurse(path + "/" + f)
        else:
            fileList.append(f)
            count += 1
    if fileList:
        orderedFiles = getOrderedFiles(fileList)
        formatNewFiles(orderedFiles, path + "/")
    return count

def sortDates():
    '''
    Moves (or copies) all files in /Unsorted to folders based on the date in
    its filename. Folders are in YYYY/MM/DD format. 
    '''

    printStatus("=================================", True)
    printStatus("Relocating files based on date...", True)
    printStatus("=================================", True, "\n\n")

    unsortedDir = thisScriptPath() + "/Unsorted"
    filesSorted = 0

    if not os.path.exists(unsortedDir):
        os.makedirs(unsortedDir)
    for f in os.listdir(unsortedDir):
        date = datetimeFromFilename(f)
        if date:
            path = date.strftime("%Y/%m/%d")
            if not isFileAlreadyHere("/Unsorted/" + f, path):
                relocateFile("/Unsorted", path, f)
                filesSorted += 1
            else:
                printStatus(f + " is already in its folder.", False, marker="NoMove")
        else:
            printStatus(f + " is not a journal file, skipping...", False)
    if (filesSorted > 0):
        printStatus("\nRelocating done! " + str(filesSorted) + " files sorted.", True, "\n\n")
    else:
        printStatus("\nNo files moved.", True, "\n\n")

def finalMove():
    '''
    Moves all files in /Unsorted into /Raw/[current date] (formatted as
    DD.MM.YY mm.ss(am/pm))
    '''
    scriptPath = thisScriptPath()
    folderContents = os.listdir(scriptPath + "/Unsorted")
    rawFolder = scriptPath + "/Raw/" + datetime.datetime.now().strftime("%d.%m.%y %I.%M.%S%p").lower()
    
    if not os.path.isdir(rawFolder):
        os.makedirs(rawFolder)
    for f in folderContents:
        move(scriptPath + "/Unsorted/" + f, rawFolder)


def sortTimes():
    printStatus("===============================", True)
    printStatus("Renaming files based on time...", True)
    printStatus("===============================", True, "\n\n")

    filesSorted = 0

    yearFolders = getYearList(os.listdir(thisScriptPath()))
    for i in yearFolders:
        filesSorted = sortTimeRecurse(i)
    if filesSorted > 0:
        printStatus("\nRenaming done! " + str(filesSorted) + " files renamed", True, "\n\n")
    else:
        printStatus("\nNo files renamed.", True, "\n\n")

def loadXmlDoc(filename):
    '''
    Attempts to load filename as an xml document and returns the root of the
    document. If it doesn't exist, it creates a new root node and returns that.
    '''
    root = None
    if os.path.exists(thisScriptPath() + "/" + filename):
        tree = ET.parse(thisScriptPath() + "/" + filename)
        root = tree.getroot()
    else:
        root = ET.Element("Journals")
    return root

def getTag(xmlDoc, tag, name):
    '''
    Searches xmlDoc for a child tag of type tag with a specified name
    attribute. Returns the result, if it can be found. Otherwise returns None.
    '''
    toReturn = None
    for child in xmlDoc:
        if child.tag == tag and child.attrib["name"] == name:
            toReturn = child
    return toReturn

def getFolderNode(xmlDoc, folder):
    node = getTag(xmlDoc, "Folder", folder)
    if not node:
        node = ET.SubElement(xmlDoc, "Folder", name=folder)
    return node

def addTagChildren(node, files):
    '''
    for every entry in files, adds a child to node. The child is a "File" tag
    with a name attribute equal to the entry in "files".
    '''
    tagsCompiled = 0
    for f in files:
        if not getTag(node, "File", f):
            ET.SubElement(node, "File", name=f)
            tagsCompiled += 1
    return tagsCompiled

def tagCompileRecurse(xmlDoc, folderPath, folder):
    '''
    Runs through all files in folderPath/folder adds them to a list, to be
    added to xmlDoc as children [see addTagChildren()]. Calls itself on all
    folders it finds in the path. Returns the amount of files added to the
    tag file.
    '''
    fullPath = thisScriptPath() + "/" + folderPath + folder + "/"
    folderContents = os.listdir(fullPath)
    files = []

    node = getFolderNode(xmlDoc, folder)
    for f in folderContents:
        if os.path.isdir(fullPath + f):
            tagCompileRecurse(node, folderPath + folder + "/", f)
        else:
            files.append(f)
    tagsCompiled = addTagChildren(node, files)
    return tagsCompiled

def prettifyXml(element):
    '''
    Converts XML to a beautified format.
    '''
    roughString = ET.tostring(element, 'utf-8')
    reparsed = xml.dom.minidom.parseString(roughString)
    return reparsed.toprettyxml(indent="\t")

def compileTags():
    printStatus("============================================", True)
    printStatus("Compiling all tag files into one big file...", True)
    printStatus("============================================", True, "\n\n")
    tagsCompiled = 0

    xmlDoc = loadXmlDoc("tags.xml")
    yearFolders = getYearList(os.listdir(thisScriptPath()))
    for i in yearFolders:
        tagsCompiled = tagCompileRecurse(xmlDoc, "/", i)
    prettified = prettifyXml(xmlDoc)
    with open("test.xml", "w") as f:
        f.write(prettified)
    
    if tagsCompiled > 0:
        printStatus("\nTag compiling done! " + str(tagsCompiled) + " files compiled", True, "\n\n")
    else:
        printStatus("\nNo tag files compiled.", True, "\n\n")

def get_arguments():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-c", "--compile", help="Combine all already existing tag files into one tag file in this script's directory", action="store_true")
    argParser.add_argument("-d", "--date", help="Put unsorted files in date folders based on time in the filename", action="store_true")
    argParser.add_argument("-t", "--time", help="Sort files in date folders based on time in the filename", action="store_true")
    argParser.add_argument("-a", "--all", help='Shorthand for "-c -d -t"', action="store_true")
    argParser.add_argument("--move", help='Move files instead of copying them', action="store_true")
    argParser.add_argument("--finalmove", help='''After date sorting, move all files in /Unsorted into /Raw/[current time]. Always moves, even without --move''', action="store_true")
    argParser.add_argument("--unsort", help='Copy sorted files back into /Unsorted', action="store_true")
    argParser.add_argument("--quiet", help='Only display messages about what major tasks are being done, and their results', action="store_true")
    argParser.add_argument("--silent", help='Display no messages', action="store_true")
    argParser.add_argument("--nomarker", help='''Don't display the markers [like this] before terminal output''', action="store_true")
    argParser.add_argument("--verbose", help='''After the program is finished, display what happened to each file''', action="store_true")
    args = argParser.parse_args()
    if len(sys.argv) == 1:
        argParser.print_help()
    return args

if __name__ == "__main__":
    resultsDate = []
    resultsTime = []
    resultsCompile = []
    resultsFinalMove = []
    args = get_arguments()
    if args.date or args.all:
        resultsDate = sortDates()
        if args.finalmove:
            resultsFinalMove = finalMove()
    if args.time or args.all:
        resultsCompile = sortTimes()
    if args.compile or args.all:
        resultsCompile = compileTags()
