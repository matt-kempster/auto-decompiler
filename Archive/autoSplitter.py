import sys, os, subprocess, glob, re


optionalArgs = "--no-andor"
optionalArgs = ""


if len(sys.argv) == 1:
    print("Usage: python3 autoSplitter.py (decomp directory)")
    exit(1)

process = subprocess.Popen(
    "git ls-files -s mips_to_c/", shell=True, stdout=subprocess.PIPE
)
mips_to_c_version = process.communicate()
mips_to_c_version = mips_to_c_version[0].decode("ascii").split()[1]

# TODO: add flag for jtable file


def splitFunc(lineStart, lineEnd, fileName, oFile):
    subprocess.call(
        "sed -n "
        + str(lineStart)
        + ","
        + str(lineEnd)
        + "p "
        + fileName
        + " > "
        + oFile,
        shell=True,
    )


def splitFunc2(lineStart, lineEnd, fileName, oFile):
    subprocess.call(
        "sed -n "
        + str(lineStart)
        + ","
        + str(lineEnd)
        + "p "
        + fileName
        + " >> "
        + oFile,
        shell=True,
    )


def getFileName(_file):
    return _file.split("/")[-1].split(".")[0]


def getFuncName(_file):
    myName = _file.split("/")[-1].split(".")[0]
    return "code_" + myName.split("_")[1]


def getNewFunc(_fileName):
    proc = subprocess.Popen(
        "./mips_to_c/mips_to_c.py "
        + optionalArgs
        + " "
        + _fileName
        + " "
        + getFileName(_fileName),
        shell=True,
        stdout=subprocess.PIPE,
    )
    return proc.communicate()[0].decode("ascii")


def valid_file(i):
    # entry and compression asm will get caught, but they should be skipped once
    # the code detects an add instruction
    return "non_matchings" not in i and "rom_header" not in i and "entry" not in i


sFiles = [
    i for i in glob.glob(sys.argv[1] + "/asm/*.s", recursive=True) if valid_file(i)
]
# print(sFiles)

for i in sFiles:
    name = getFileName(i)
    os.system("mkdir -p " + sys.argv[1] + "/asm/non_matchings/" + name)

symReference = {}
lastSymInFile = []
curr_sym = ""
sectionStart = 0
jrraCounter = -1
fileStartAddr = ""
gotFirstFunc = 0
# finds evidence of handwritten asm (the most common sign being the add instruction)
myRe = re.compile(r"\badd\b[^.]")
print("Splitting ASM files...")
for i in sFiles:
    lineNum = 1

    oFileName = sys.argv[1] + "/src/" + getFileName(i) + ".c"
    oFile = open(oFileName, "w+")

    tmpFile = open(i, "r")
    num_lines = sum(1 for line in tmpFile)
    num_lines -= 1
    tmpFile.close()
    tmpFile = open(i, "r")
    buff = tmpFile.read()
    matches = myRe.findall(buff)
    print(matches, i)
    if len(matches) != 0:
        tmpFile.close()
        continue
    tmpFile.close()

    with open(i, "r") as iFile:
        for line in iFile:
            if "/*" in line and fileStartAddr == "":
                fileStartAddr = line.split()[2]
            if ".section .text" in line:
                sectionStart = lineNum
            if "glabel" in line and "D_" not in line and "L8" not in line:
                symReference[line.split()[-1]] = [lineNum]
                if curr_sym != "":
                    symReference[curr_sym].append(lineNum)
                    # print(symReference[curr_sym][0], lineNum - 1, i, sys.argv[1]+"/asm/non_matchings/"+getFileName(i)+"/"+curr_sym+".s")
                    splitFunc(
                        symReference[curr_sym][0],
                        lineNum - 1,
                        i,
                        sys.argv[1]
                        + "/asm/non_matchings/"
                        + getFileName(i)
                        + "/"
                        + curr_sym
                        + ".s",
                    )
                curr_sym = line.split()[-1]
                lastSymInFile = []
                lastSymInFile.append(curr_sym)
                lastSymInFile.append(lineNum)
            lineNum += 1
        # print(lastSymInFile[1], num_lines, i, sys.argv[1]+"/asm/non_matchings/"+getFileName(i)+"/"+curr_sym+".s")
        if len(symReference) != 0:
            splitFunc(
                lastSymInFile[1],
                num_lines,
                i,
                sys.argv[1]
                + "/asm/non_matchings/"
                + getFileName(i)
                + "/"
                + curr_sym
                + ".s",
            )
        else:
            os.system(
                'echo "glabel func_'
                + fileStartAddr
                + '" >> '
                + sys.argv[1]
                + "/asm/non_matchings/"
                + getFileName(i)
                + "/"
                + getFileName(i)
                + ".s"
            )
            # splitFunc2(sectionStart + 1, num_lines, i, sys.argv[1]+"/asm/non_matchings/"+getFileName(i)+"/"+getFileName(i)+".s")
    os.system("cat prelude.inc > " + sys.argv[1] + "/src/" + getFileName(i) + ".c")

    print("Writing to", oFileName)
    for sym in symReference:
        oFile.write("#ifdef MIPS_TO_C\n")
        oFile.write("//generated by mips_to_c commit " + mips_to_c_version + "\n")
        oFile.write(
            getNewFunc(
                sys.argv[1] + "/asm/non_matchings/" + getFileName(i) + "/" + sym + ".s "
            )
        )
        oFile.write("#else\n")
        oFile.write(
            'GLOBAL_ASM("asm/non_matchings/' + getFileName(i) + "/" + sym + '.s")\n'
        )
        oFile.write("#endif\n\n")
    if len(symReference) == 0:
        oFile.write(
            'GLOBAL_ASM("asm/non_matchings/'
            + getFileName(i)
            + "/"
            + getFileName(i)
            + '.s")\n'
        )
    symReference = {}
    curr_sym = ""
    sectionStart = 0
    fileStartAddr = ""
    gotFirstFunc = 0
