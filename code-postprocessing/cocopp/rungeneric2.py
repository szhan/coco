#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Routines for the comparison of 2 algorithms.

Synopsis:
    ``python -m cocopp.rungeneric2 [OPTIONS] FOLDER_NAME1 FOLDER_NAME2...``

Help:
    ``python -m cocopp.rungeneric2 --help``

"""

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import warnings
import getopt

from . import genericsettings, ppfig, toolsdivers, rungenericmany, findfiles
from .toolsdivers import print_done
from .compall import pptables

# genericsettings.summarized_target_function_values[0] might be another option

from . import pproc
from . import config
from . import testbedsettings
from . import pprldistr
from .pproc import DataSetList, processInputArgs
from .ppfig import Usage
from .toolsdivers import prepend_to_file, replace_in_file, strip_pathname1, str_to_latex
from .comp2 import ppfig2, pprldistr2, ppscatter
from .compall import ppfigs, pprldmany
from . import ppconverrorbars
import matplotlib.pyplot as plt

__all__ = ['main']


def usage():
    print(main.__doc__)


def main(argv=None):
    r"""Routine for post-processing COCO data from two algorithms.

    Provided with some data, this routine outputs figure and TeX files
    in a folder needed for the compilation of the provided LaTeX templates
    for comparing two algorithms (``*cmp.tex`` or ``*2*.tex``).

    The used template file needs to be edited so that the command
    ``\bbobdatapath`` points to the output folder created by this routine.

    The output files will contain performance tables, performance
    scaling figures and empirical cumulative distribution figures. On
    subsequent executions, new files will be added to the output folder,
    overwriting existing older files in the process.

    Keyword arguments:

    *argv* -- list of strings containing options and arguments. If not
    given, sys.argv is accessed.

    *argv* must list folders containing BBOB data files. Each of these
    folders should correspond to the data of ONE algorithm.

    Furthermore, argv can begin with, in any order, facultative option
    flags listed below.

        -h, --help
            displays this message.
        -v, --verbose
            verbose mode, prints out operations.
        -o OUTPUTDIR, --output-dir=OUTPUTDIR
            changes the default output directory (:file:`ppdata`) to
            :file:`OUTPUTDIR`
        --noise-free, --noisy
            processes only part of the data.
        --settings=SETTINGS
            changes the style of the output figures and tables. At the
            moment the only differences are  in the colors of the output
            figures. SETTINGS can be either "grayscale" or "color".
            The default setting is "color".
        --fig-only, --rld-only, --tab-only, --sca-only
            these options can be used to output respectively the aRT
            graphs figures, run length distribution figures or the
            comparison tables scatter plot figures only. Any combination
            of these options results in no output.
        --no-rld-single-fcts
            do not generate runlength distribution figures for each
            single function.
        --expensive
            runlength-based f-target values and fixed display limits,
            useful with comparatively small budgets.
        --no-svg
            do not generate the svg figures which are used in html files

    Exceptions raised:

    *Usage* -- Gives back a usage message.

    Examples:

    * Calling the rungeneric2.py interface from the command line::

        $ python -m cocopp.rungeneric2 -v Alg0-baseline Alg1-of-interest

      will post-process the data from folders :file:`Alg0-baseline` and
      :file:`Alg1-of-interest`, the former containing data for the
      reference algorithm (zero-th) and the latter data for the
      algorithm of concern (first). The results will be output in the
      default output folder. The ``-v`` option adds verbosity.

    * From the python interpreter (requires that the path to this
      package is in python search path; most simply achieved by running
      `python do.py install-postprocessing`)::

        >> import cocopp as pp
        >> pp.rungeneric2.main('-o outputfolder PSO DEPSO'.split())

    This will execute the post-processing on the data found in folder
    :file:`PSO` and :file:`DEPSO`. The ``-o`` option changes the output
    folder from the default to :file:`outputfolder`.

    """

    if argv is None:
        argv = sys.argv[1:]
        # The zero-th input argument which is the name of the calling script is
        # disregarded.

    try:

        try:
            opts, args = getopt.getopt(argv, genericsettings.shortoptlist,
                                       genericsettings.longoptlist)
        except getopt.error, msg:
            raise Usage(msg)

        if not args:
            usage()
            sys.exit()

        # Process options
        outputdir = genericsettings.outputdir
        for o, a in opts:
            if o in ("-v", "--verbose"):
                genericsettings.verbose = True
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-o", "--output-dir"):
                outputdir = a
            elif o == "--fig-only":
                genericsettings.isRLDistr = False
                genericsettings.isTab = False
                genericsettings.isScatter = False
            elif o == "--rld-only":
                genericsettings.isFig = False
                genericsettings.isTab = False
                genericsettings.isScatter = False
            elif o == "--tab-only":
                genericsettings.isFig = False
                genericsettings.isRLDistr = False
                genericsettings.isScatter = False
            elif o == "--sca-only":
                genericsettings.isFig = False
                genericsettings.isRLDistr = False
                genericsettings.isTab = False
            elif o == "--noisy":
                genericsettings.isNoisy = True
            elif o == "--noise-free":
                genericsettings.isNoiseFree = True
            elif o == "--settings":
                genericsettings.inputsettings = a
            elif o == "--no-rld-single-fcts":
                genericsettings.isRldOnSingleFcts = False
            elif o == "--runlength-based":
                genericsettings.runlength_based_targets = True
            elif o == "--expensive":
                genericsettings.isExpensive = True  # comprises runlength-based
            elif o == "--no-svg":
                genericsettings.generate_svg_files = False
            elif o == "--los-only":
                warnings.warn("option --los-only will have no effect with rungeneric2.py")
            elif o == "--crafting-effort=":
                warnings.warn("option --crafting-effort will have no effect with rungeneric2.py")
            elif o in ("-p", "--pickle"):
                warnings.warn("option --pickle will have no effect with rungeneric2.py")
            else:
                assert False, "unhandled option"

        # from cocopp import bbob2010 as inset # input settings
        if genericsettings.inputsettings == "color":
            from . import genericsettings as inset  # input settings
            config.config()
        elif genericsettings.inputsettings == "grayscale":  # probably very much obsolete
            from . import grayscalesettings as inset  # input settings
        elif genericsettings.inputsettings == "black-white":  # probably very much obsolete
            from . import bwsettings as inset  # input settings
        else:
            txt = ('Settings: %s is not an appropriate ' % genericsettings.inputsettings
                   + 'argument for input flag "--settings".')
            raise Usage(txt)

        if not genericsettings.verbose:
            warnings.simplefilter('module')
            warnings.simplefilter('ignore')

        print("\nPost-processing (2): will generate comparison " +
              "data in folder %s" % outputdir)
        print("  this might take several minutes.")

        dsList, sortedAlgs, dictAlg = processInputArgs(args)

        if 1 < 3 and len(sortedAlgs) != 2:
            raise ValueError('rungeneric2.py needs exactly two algorithms to '
                             + 'compare, found: ' + str(sortedAlgs)
                             + '\n use rungeneric.py (or rungenericmany.py) to '
                             + 'compare more algorithms. ')

        if not dsList:
            sys.exit()

        if (any(ds.isBiobjective() for ds in dsList)
            and any(not ds.isBiobjective() for ds in dsList)):
            sys.exit()

        for i in dictAlg:
            if genericsettings.isNoisy and not genericsettings.isNoiseFree:
                dictAlg[i] = dictAlg[i].dictByNoise().get('nzall', DataSetList())
            if genericsettings.isNoiseFree and not genericsettings.isNoisy:
                dictAlg[i] = dictAlg[i].dictByNoise().get('noiselessall', DataSetList())

        for i in dsList:
            if i.dim not in genericsettings.dimensions_to_display:
                continue
            # check whether current set of instances correspond to correct
            # setting of a BBOB workshop and issue a warning otherwise:            
            curr_instances = (dict((j, i.instancenumbers.count(j)) for j in set(i.instancenumbers)))
            correct = False
            for instance_set_of_interest in inset.instancesOfInterest:
                if curr_instances == instance_set_of_interest:
                    correct = True
            if not correct:
                warnings.warn('The data of %s do not list ' % i +
                              'the correct instances ' +
                              'of function F%d.' % i.funcId)

        if len(sortedAlgs) < 2:
            raise Usage('Expect data from two different algorithms, could ' +
                        'only find one.')
        elif len(sortedAlgs) > 2:
            warnings.warn('Data from folders: %s ' % (sortedAlgs) +
                          'were found, the first two will be processed.')

        # Group by algorithm
        dsList0 = dictAlg[sortedAlgs[0]]
        if not dsList0:
            raise Usage('Could not find data for algorithm %s.' % (sortedAlgs[0]))

        dsList1 = dictAlg[sortedAlgs[1]]
        if not dsList1:
            raise Usage('Could not find data for algorithm %s.' % (sortedAlgs[0]))

        # get the name of each algorithm from the input arguments
        tmppath0, alg0name = os.path.split(sortedAlgs[0].rstrip(os.sep))
        tmppath1, alg1name = os.path.split(sortedAlgs[1].rstrip(os.sep))

        for i in dsList0:
            testbedsettings.copy_reference_values(i.algId, alg0name)
            i.algId = alg0name
        for i in dsList1:
            testbedsettings.copy_reference_values(i.algId, alg1name)
            i.algId = alg1name

        config.target_values(genericsettings.isExpensive)
        config.config(dsList[0].testbed_name)

        ######################### Post-processing #############################
        latex_commands_file = os.path.join(outputdir, 'cocopp_commands.tex')

        algorithm_folder = findfiles.get_output_directory_sub_folder(sortedAlgs)
        prepend_to_file(latex_commands_file, ['\\providecommand{\\algsfolder}{' + algorithm_folder + '/}'])
        two_algorithms_output = os.path.join(outputdir, algorithm_folder)

        abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if genericsettings.isFig or genericsettings.isRLDistr or genericsettings.isTab or genericsettings.isScatter:
            if not os.path.exists(outputdir):
                os.mkdir(outputdir)
                if genericsettings.verbose:
                    print('Folder %s was created.' % outputdir)
            if not os.path.exists(two_algorithms_output):
                os.mkdir(two_algorithms_output)
                if genericsettings.verbose:
                    print('Folder %s was created.' % two_algorithms_output)

            # prepend the algorithm name command to the tex-command file
            lines = []
            for i, alg in enumerate(args):
                lines.append('\\providecommand{\\algorithm' + abc[i] + '}{' +
                             str_to_latex(strip_pathname1(alg)) + '}')
            prepend_to_file(latex_commands_file,
                            lines, 1000, 'bbob_proc_commands.tex truncated, '
                            + 'consider removing the file before the text run'
                            )

        # Check whether both input arguments list noisy and noise-free data
        dictFN0 = dsList0.dictByNoise()
        dictFN1 = dsList1.dictByNoise()
        k0 = set(dictFN0.keys())
        k1 = set(dictFN1.keys())
        symdiff = k1 ^ k0  # symmetric difference
        if symdiff:
            tmpdict = {}
            for i, noisegrp in enumerate(symdiff):
                tmp = None
                tmp2 = None
                if noisegrp == 'nzall':
                    tmp = 'noisy'
                elif noisegrp == 'noiselessall':
                    tmp = 'noiseless'

                if dictFN0.has_key(noisegrp):
                    tmp2 = sortedAlgs[0]
                elif dictFN1.has_key(noisegrp):
                    tmp2 = sortedAlgs[1]

                if tmp and tmp2:
                    tmpdict.setdefault(tmp2, []).append(tmp)

            txt = []
            for i, j in tmpdict.iteritems():
                txt.append('Only input folder %s lists %s data.'
                           % (i, ' and '.join(j)))
            raise Usage('Data Mismatch: \n  ' + ' '.join(txt) + '\nTry using --noise-free or --noisy flags.')

        algName0 = toolsdivers.str_to_latex(
            set(i[0] for i in dsList0.dictByAlg().keys()).pop().replace(genericsettings.extraction_folder_prefix, ''))
        algName1 = toolsdivers.str_to_latex(
            set(i[0] for i in dsList1.dictByAlg().keys()).pop().replace(genericsettings.extraction_folder_prefix, ''))

        algorithm_name = "%s vs %s" % (algName1, algName0)
        ppfig.save_single_functions_html(
            os.path.join(two_algorithms_output, genericsettings.ppfigs_file_name),
            algname=algorithm_name,
            htmlPage=ppfig.HtmlPage.PPFIGS,
            function_groups=dsList0.getFuncGroups(),
            parentFileName=genericsettings.many_algorithm_file_name
        )

        ppfig.save_single_functions_html(
            os.path.join(two_algorithms_output, genericsettings.ppscatter_file_name),
            algname=algorithm_name,
            htmlPage=ppfig.HtmlPage.PPSCATTER,
            function_groups=dsList0.getFuncGroups(),
            parentFileName=genericsettings.many_algorithm_file_name
        )

        ppfig.save_single_functions_html(
            os.path.join(two_algorithms_output, genericsettings.pprldistr2_file_name),
            algname=algorithm_name,
            htmlPage=ppfig.HtmlPage.PPRLDISTR2,
            function_groups=dsList0.getFuncGroups(),
            parentFileName=genericsettings.many_algorithm_file_name
        )

        dictDim0 = dsList0.dictByDim()
        dictDim1 = dsList1.dictByDim()

        ppfig.save_single_functions_html(
            os.path.join(two_algorithms_output, genericsettings.pptables_file_name),
            '',  # algorithms names are clearly visible in the figure
            dimensions=sorted(list(set(dictDim0.keys()) & set(dictDim1.keys()))),
            htmlPage=ppfig.HtmlPage.PPTABLES,
            function_groups=dsList0.getFuncGroups(),
            parentFileName=genericsettings.many_algorithm_file_name
        )

        if genericsettings.isFig:
            print("log aRT1/aRT0 vs target function values...")
            plt.rc("axes", **inset.rcaxeslarger)
            plt.rc("xtick", **inset.rcticklarger)
            plt.rc("ytick", **inset.rcticklarger)
            plt.rc("font", **inset.rcfontlarger)
            plt.rc("legend", **inset.rclegendlarger)
            plt.rc('pdf', fonttype=42)
            ppfig2.main(dsList0, dsList1, testbedsettings.current_testbed.ppfig2_ftarget,
                        two_algorithms_output)
            print_done()

        plt.rc("axes", **inset.rcaxes)
        plt.rc("xtick", **inset.rctick)
        plt.rc("ytick", **inset.rctick)
        plt.rc("font", **inset.rcfont)
        plt.rc("legend", **inset.rclegend)
        plt.rc('pdf', fonttype=42)

        if genericsettings.isRLDistr:
            print("ECDF runlength ratio graphs...")
            if len(dictFN0) > 1 or len(dictFN1) > 1:
                warnings.warn('Data for functions from both the noisy and ' +
                              'non-noisy testbeds have been found. Their ' +
                              'results will be mixed in the "all functions" ' +
                              'ECDF figures.')

            # ECDFs of aRT ratios
            for dim in set(dictDim0.keys()) & set(dictDim1.keys()):
                if dim in inset.rldDimsOfInterest:
                    # ECDF for all functions altogether
                    try:
                        pprldistr2.main(dictDim0[dim], dictDim1[dim], dim,
                                        testbedsettings.current_testbed.rldValsOfInterest,
                                        two_algorithms_output,
                                        '%02dD_all' % dim)
                    except KeyError:
                        warnings.warn('Could not find some data in %d-D.' % dim)
                        continue

                    # ECDFs per function groups
                    dictFG0 = dictDim0[dim].dictByFuncGroup()
                    dictFG1 = dictDim1[dim].dictByFuncGroup()

                    for fGroup in set(dictFG0.keys()) & set(dictFG1.keys()):
                        pprldistr2.main(dictFG1[fGroup], dictFG0[fGroup], dim,
                                        testbedsettings.current_testbed.rldValsOfInterest,
                                        two_algorithms_output,
                                        '%02dD_%s' % (dim, fGroup))

                    # ECDFs per noise groups
                    dictFN0 = dictDim0[dim].dictByNoise()
                    dictFN1 = dictDim1[dim].dictByNoise()

                    for fGroup in set(dictFN0.keys()) & set(dictFN1.keys()):
                        pprldistr2.main(dictFN1[fGroup], dictFN0[fGroup], dim,
                                        testbedsettings.current_testbed.rldValsOfInterest,
                                        two_algorithms_output,
                                        '%02dD_%s' % (dim, fGroup))

            prepend_to_file(latex_commands_file,
                            ['\\providecommand{\\bbobpprldistrlegendtwo}[1]{',
                             pprldistr.caption_two(),  # depends on the config
                             # setting, should depend
                             # on maxfevals
                             '}'
                             ])
            print_done()

            # ECDFs per noise groups, code copied from rungenericmany.py
            # (needed for bbob-biobj multiple algo template)
            print("ECDF graphs per noise group...")
            rungenericmany.grouped_ecdf_graphs(
                pproc.dictAlgByNoi(dictAlg),
                sortedAlgs,
                two_algorithms_output,
                dictAlg[sortedAlgs[0]].getFuncGroups(),
                inset,
                genericsettings.many_algorithm_file_name)
            print_done()

            # ECDFs per function groups, code copied from rungenericmany.py
            # (needed for bbob-biobj multiple algo template)
            print("ECDF runlength graphs per function group...")
            rungenericmany.grouped_ecdf_graphs(
                pproc.dictAlgByFuncGroup(dictAlg),
                sortedAlgs,
                two_algorithms_output,
                dictAlg[sortedAlgs[0]].getFuncGroups(),
                inset,
                genericsettings.many_algorithm_file_name)
            print_done()

            if testbedsettings.current_testbed not in [testbedsettings.GECCOBiObjBBOBTestbed,
                                                       testbedsettings.GECCOBiObjExtBBOBTestbed]:
                print("ECDF runlength graphs...")
                for dim in set(dictDim0.keys()) & set(dictDim1.keys()):
                    pprldistr.fmax = None  # Resetting the max final value
                    pprldistr.evalfmax = None  # Resetting the max #fevalsfactor
                    # ECDFs of all functions altogether
                    if dim in inset.rldDimsOfInterest:
                        try:
                            pprldistr.comp(dictDim1[dim], dictDim0[dim],
                                           testbedsettings.current_testbed.rldValsOfInterest,
                                           # TODO: let rldVals... possibly be RL-based targets
                                           True,
                                           two_algorithms_output, 'all')
                        except KeyError:
                            warnings.warn('Could not find some data in %d-D.'
                                          % (dim))
                            continue
    
                        # ECDFs per function groups
                        dictFG0 = dictDim0[dim].dictByFuncGroup()
                        dictFG1 = dictDim1[dim].dictByFuncGroup()
    
                        for fGroup in set(dictFG0.keys()) & set(dictFG1.keys()):
                            pprldistr.comp(dictFG1[fGroup], dictFG0[fGroup],
                                           testbedsettings.current_testbed.rldValsOfInterest, True,
                                           two_algorithms_output,
                                           '%s' % fGroup)
    
                        # ECDFs per noise groups
                        dictFN0 = dictDim0[dim].dictByNoise()
                        dictFN1 = dictDim1[dim].dictByNoise()
                        for fGroup in set(dictFN0.keys()) & set(dictFN1.keys()):
                            pprldistr.comp(dictFN1[fGroup], dictFN0[fGroup],
                                           testbedsettings.current_testbed.rldValsOfInterest, True,
                                           two_algorithms_output,
                                           '%s' % fGroup)
                print_done() # of "ECDF runlength graphs..."

            # copy-paste from above, here for each function instead of function groups
            if genericsettings.isRldOnSingleFcts:
                print("ECDF graphs per function...")
                # ECDFs for each function
                pprldmany.all_single_functions(dictAlg,
                                               False,
                                               sortedAlgs,
                                               two_algorithms_output,
                                               genericsettings.many_algorithm_file_name,
                                               settings=inset)
                print_done()

        html_file_name = os.path.join(two_algorithms_output, genericsettings.ppscatter_file_name + '.html')

        if genericsettings.isScatter:
            print("Scatter plots...")
            ppscatter.main(dsList1, dsList0, two_algorithms_output, inset)
            prepend_to_file(latex_commands_file,
                            ['\\providecommand{\\bbobppscatterlegend}[1]{',
                             ppscatter.figure_caption(),
                             '}'
                             ])

            replace_in_file(html_file_name, '##bbobppscatterlegend##', ppscatter.figure_caption(True))
            for i, alg in enumerate(args):
                replace_in_file(html_file_name, 'algorithm' + abc[i], str_to_latex(strip_pathname1(alg)))

            print_done()

        if genericsettings.isTab:
            # The following is copied from rungenericmany.py to comply
            # with the bi-objective many-algorithm LaTeX template
            print("Generating new tables (pptables.py)...")
            prepend_to_file(latex_commands_file,
                            ['\providecommand{\\bbobpptablesmanylegend}[2]{' +
                             pptables.get_table_caption() + '}'])
            dictNoi = pproc.dictAlgByNoi(dictAlg)
            for ng, tmpdictng in dictNoi.iteritems():
                dictDim = pproc.dictAlgByDim(tmpdictng)
                for d, tmpdictdim in sorted(dictDim.iteritems()):
                    pptables.main(
                        tmpdictdim,
                        sortedAlgs,
                        two_algorithms_output,
                        ([1, 20, 38] if (testbedsettings.current_testbed.name ==
                                         testbedsettings.testbed_name_bi) else True),
                        latex_commands_file)
            print_done()

        if genericsettings.isScaleUp:
            print("Scaling figures...")
            plt.rc("axes", labelsize=20, titlesize=24)
            plt.rc("xtick", labelsize=20)
            plt.rc("ytick", labelsize=20)
            plt.rc("font", size=20)
            plt.rc("legend", fontsize=20)
            plt.rc('pdf', fonttype=42)

            ppfigs.main(dictAlg,
                        genericsettings.ppfigs_file_name,
                        sortedAlgs,
                        two_algorithms_output,
                        latex_commands_file)
            plt.rcdefaults()
            print_done()

        ppfig.save_single_functions_html(
            os.path.join(two_algorithms_output, genericsettings.many_algorithm_file_name),
            algname=algorithm_name,
            htmlPage=ppfig.HtmlPage.TWO,

            function_groups=dsList0.getFuncGroups())

        if (genericsettings.isFig or genericsettings.isRLDistr
            or genericsettings.isTab or genericsettings.isScatter
            or genericsettings.isScaleUp):
            print("Output data written to folder %s" % outputdir)

        plt.rcdefaults()

    except Usage, err:
        print(err.msg, file=sys.stderr)
        print("For help use -h or --help", file=sys.stderr)
        return 2

    return DataSetList(dsList).dictByAlg()