import os
import re
import sys
import html
import json

from collections import defaultdict
from copy import deepcopy
from datetime import date

from xmi_document import xmi_document
from nltk import PorterStemmer
from reversestem import unstem

try:
    fn = sys.argv[1]
    try:
        output_dir = sys.argv[2]
    except IndexError as e:
        OUTPUT = sys.stdout
except:
    print("Usage: python to_bsdd.py <schema.xml> <output_dir>", file=sys.stderr)
    exit()

xmi_doc = xmi_document(fn)
xmi_doc.should_translate_pset_types = False
bfn = os.path.basename(fn)

ps = PorterStemmer()
words_to_catch = sorted(['current','cost','of','switch','order','recovery','loading','barrier','predefined','reel','basin','fountain','packaged','nozzle','tube','plant',
                         'injection','assisted','element','vertically','vertical','turbine','heating','disassembly','button','component','security','deflector',
                         'cabinet','assembly','actuator','meter','sensor','object','detection','station','depth','controller','terminal','center','frame','electric',
                         'exchangers','wedge','gate','configured','plug','lubricated','parallel','slide','exchange','exchanger','change','outlet','server','plate','expansion',
                         'rail','solar','surcharge','excavation','combustion','draft','mechanical','constant','coil','cooled','cooler','evaporative','pavement','top',
                         'column','traffic','crossing','side','road','vehicle','island','gear','super','event','adiabatic','segment','marker','structure','ground',
                         'channel','pressure','shift','prevention','tray','provision','soil','preloaded','water','cold','hot','cable','domestic','power','generation',
                         'solid','waste','unit','carrier','duct','protection','disconnector','surfacing','breaker','wall','flow','curve','limiter','board','chamber',
                         'panel','acoustic','fire','inspection','transverse','rumble','strip','surface','maintenance','of','pier','system','fixed','hatch','transmission',
                         'network','machine','device','equipment','sound','stud','connector','marking','removal','space','agent','section','inventory','bill','schedule','rate',
                         'void','quantities','compacted','drained','tower','indirect','direct','media','intelligent','rigid','random','marine','compact','tensioner',
                         'operational','intermediate','storage','hooks','area','lift','lifting','forward','natural','radial','gravity','piston','relief','air','track', 'pair',
                         'switching','transition','off','bend','circular','derailer','tracked','roadway','plateau','retention','stock','double','twin','cage','seat',
                         'moving','soft','inlet','symbol','symbolic','toilet','dock','docking','parabolic','bending','transceiver','control','asset','furniture',
                         'contact','centre','motorized','motor','photocopier','generator','engine','point','access','asynchronous','synchronous','single','plaza','wheel','loops',
                         'drive','stop','rates','timer','leakage','time','dryer','framework','roof','induction','topping','alignment','curved','stair','elemented','scaffolding',
                         'electrical','chair','sofa','railway','entrance','secured','cover','manhole','flat','concave','convex','known','cylinder','horizontal','business','issues',
                         'elevated','work','platform','materials','handling','material','effects','health','safety','hazadrous','dust','scaffold','fall','fragile','shock',
                         'environmental','drowning','flooding','very','high','unintended','collapse','working','overhead','considerable','value','driven','defined','unknown',
                         'class','appliance','earth','protective','neutral','disposal','cradle','site','production','transport','repair','whole','lifecycle','siphon',
                         'urgent','procedure','emergency','offsite','very','office','sensors','volume','diffusers','variable','multiple','zone','conduit','temperature','powered',
                         'safety','light','warning','exit','blue','illumination','spark','gap','gas','filled','touch','screen','buttons','auto','transformer','divided','support',
                         'earthing','offload','break','glass','key','operated','manual','pull','cord','exhaust','damper','shell','pump','filter','conveyor','pumps','heat','heated',
                         'speed','fan','bypass','valve','dampers','wet','bulb','reset','exiting','folding','curtain','closed','circuit','dry','open','indicator','shunting','route',
                         'derail','departure','starting','signal','repeating','obstruction','hump','auxiliary','home','distant','block','blocking','approach','mesh','push',
                         'pushing', 'bidirectional','directional','right','left','damper','balancing','combination','earthquake','relay','interface','face','nail','loss',
                         'track','mounted','unidirectional','blastdamper','centrifugal','backward','inclined','vane','axial','propellor','diatomaceous','earth','reverse','osmosis',
                         'liquefied','petroleum','lightning','shaft','soak','slurry','collector','with','check','commercial','propane','butane','atmospheric','vacuum','wetted',
                         'function','complementary','circuit','fault','lower','limit','control','pulse','converter','running','average','upper','limit','control','lower','band',
                         'position','frost','automatic','continuous','source','sink'], key=len)[::-1]

all_caps = ['ups','gprs','rs','am','gps','dc','ac','chp','led','oled','ole','gfa','tv','msc','ppm','iot','ocl','lrm','cgt','teu','tmp','std','gsm','cdma','lte','td','scdma','wcdma','sc','mp','bm','ol','ep']
small_caps = ['for','of','and','to','with','or','at']

schema_name = xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:Package"][1].name.replace("exp", "").upper()
schema_name = "".join(["_", c][c.isalnum()] for c in schema_name)
schema_name = re.sub(r"_+", "_", schema_name)
schema_name = schema_name.strip('_')

def yield_parents(node):
    yield node
    if node.parentNode:
        yield from yield_parents(node.parentNode)

def get_path(xmi_node):
    nodes = list(yield_parents(xmi_node.xml))
    def get_name(n):
        if n.attributes:
            v = n.attributes.get('name')
            if v: return v.value
    node_names = [get_name(n) for n in nodes]
    return node_names[::-1]
    
included_packages = set(("IFC 4.2 schema (13.11.2019)", "Common Schema", "IFC Ports and Waterways", "IFC Road", "IFC Rail - PSM"))

def skip_by_package(element):
    return not (set(get_path(xmi_doc.by_id[element.idref])) & included_packages)
    
HTML_TAG_PATTERN = re.compile('<.*?>')
MULTIPLE_SPACE_PATTERN = re.compile(r'\s+')
# CHANGE_LOG_PATTERN = re.compile(r'\{\s*\.change\-\w+\s*\}.+', flags=re.DOTALL)
CURLY_BRACKET_PATTERN = re.compile('{.*?}.*') #also removes all text after curly brackets
FIGURE_PATTERN = re.compile('[^.,;]*(Figure|the figure)[^.,;]*') #removes the sentence when it mentiones a Figure.

def strip_html(s, trim=True):
    try:
        s1 = html.unescape(s)
    except TypeError:
        # error when name contains link, for example: "https://github.com/buildingSMART/IFC4.3.x-development/edit/master/docs/schemas/core/IfcProductExtension/Types/IfcAlignmentTypeEnum.md#L0 has no content"
        s1 = ''
    if trim:
        # split and remove on keywords:
        i = min([x for x in [s1.find('NOTE'), s1.find('DIAGRAM'), s1.find('CHANGE'), s1.find('IFC4'), s1.find('HISTORY'), s1.find('EXAMPLE'), s1.find('DEPRECATION'), 1e5] if x >= 0])
        if i > 0 and i != 1e5:
            s1 = s1[:i]
        elif i==0:
            # some descriptions start with History or Note. Don't want them.
            s1 = ""
    s2 = re.sub('\n', '; ', s1)
    s3 = re.sub(':', ': ', s2)
    s4 = re.sub(HTML_TAG_PATTERN, ' ', s3)
    s5 = re.sub(CURLY_BRACKET_PATTERN, ' ', s4)
    s6 = re.sub(r'SELF\\', '', s5)
    s7 = re.sub(r"\s+", " ", s6)
    s8 = re.sub(FIGURE_PATTERN, '', s7)
    s9 = re.sub(MULTIPLE_SPACE_PATTERN, ' ', s8).strip()
    # TODO too long description...
    # sx = re.sub('e.g.', "", re.sub('i.e.', "", re.sub('etc.', "", s9)))
    # if len(sx.split(".")) > 6:
    #     s9 = s9.split(sx.split(".")[6])[0] + "[IT WAS CUT HERE!]"
    return s9

def skip_empty(s):
    if str(type(s)) == "<class 'xmi_document.missing_markdown'>":
        s = ""
    return s

def caps_control(s):
    s1 = s.split()
    if isinstance(s1, list):
        for part in s1:
            for a in all_caps:
                if part.lower() == a:
                    s = re.sub(part, a.upper(), s)
            for b in small_caps:
                if part.lower() == b:
                    s = re.sub(part, b.lower(), s)
    return s


def split_at_word(w, s):
    
    if w != '' and ((ps.stem(w) in s.lower()) or (w in s.lower())):
        # to_keep=False
        # for wtk in words_to_keep:
        #     if wtk in s.lower():
        #         to_keep=True
        # if not to_keep:
        if w in s.lower():
            s = re.sub(w, " "+w+" ", s.lower())
        else: 
            vs = unstem(ps.stem(w))
            if isinstance(vs, dict):
                # turn dict to flat list
                vsl = []
                for key, val in vs.items():
                    vsl.append(key)
                    if val:
                        for v in val:
                            vsl.append(v)
                vs = vsl
            if vs:
                vs.append(ps.stem(w))
                vs = sorted(vs, key=len)[::-1]
                for v in vs:
                    if v in s.lower():
                        s = re.sub(w, " "+w+" ", s.lower())
                        break
    if isinstance(s, list):
        s = " ".join(s)
    return s

def split_words(s):
    # hard-coded list of words found in enumerations to split the ALLCAPS phrases into indivudual words. List might not be complete
    found_words = []
    for w in words_to_catch:
        # skip if word is contained in previous words (e.g. EXCHANGE in EXCHANGER)
        previously_found = False
        for fw in found_words:
            if w in fw:
                previously_found = True
        if not previously_found:
            s2 = deepcopy(s)
            s2 = split_at_word(w, s2)
            if s2 != s:
                found_words.append(w)
                s = s2
    s = re.sub("_", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def quote(s):
    return '"%s"' % s

def annotate(s):
    if isinstance(s, str) or len(s) > 0:
        return re.sub(all_codes, lambda match: "[[%s]]" % match.group(0), s)
    else:
        # an empty defaultdict
        return ""

def normalise(s):
    """ format the text by spliting into separate words."""    
    if isinstance(s, str) or len(s) > 0:
        # split CamelCase:
        s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)
        return re.sub(MULTIPLE_SPACE_PATTERN, ' ', s).strip()
    else:
        # an empty defaultdict
        return ""

def clean(s):
    """ format the text by removing unwanted characters."""    
    if isinstance(s, str) or len(s) > 0:
        # remove all redundant characters (except those listed):
        clean = ''.join(['', c][c.isalnum() or c in ':.,()-+ —=;α°_/!?$%@<>\*'] for c in s)
        return re.sub(MULTIPLE_SPACE_PATTERN, ' ', clean).strip()
    else:
        # an empty defaultdict
        return ""
    
def generalization(pe):
    try:
        P = xmi_doc.xmi.by_id[(pe|"generalization").general]
    except:
        P = None
    if P: 
        return generalization(P)
    else: 
        return pe


type_to_values = {
    'boolean': ["TRUE","FALSE"],
    'logical': ["TRUE","FALSE","UNKNOWN"],
}

def generate_definitions():
    """
    A generator that yields tuples of <a, b> with
    a: location in file
    a: a fully qualifying key as tuple
    b: the documentation string
    """
    make_defaultdict = lambda: defaultdict(make_defaultdict)
    classes = defaultdict(make_defaultdict)
    
    def get_parent_of_pt(enum_type):
        enum_id = enum_type.idref
        type_refs = []
        for assoc in xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:Association"]:
            try:
                c1, c2 = assoc/'ownedEnd'
            except ValueError as e:
                # print("encountered exception `%s' on %s" % (e, assoc))
                continue
            assoc_type_refs = set(map(lambda c: (c|"type").idref, (c1, c2)))
            if enum_id in assoc_type_refs:
                other_idref = list(assoc_type_refs - {enum_id})[0]
                type_refs.append(xmi_doc.xmi.by_id[other_idref].name)
                
        # @todo filter this based on inheritance hierarchy
        type_refs_without_type = [s for s in type_refs if 'Type' not in s]
        if len(type_refs_without_type) != 1:
            print("WARNING:", len(type_refs_without_type), "type associations on", enum_type.name, file=sys.stderr)
        
        return type_refs_without_type[0] if type_refs_without_type else None
    
    class_name_to_node = {}
    
    by_id = {}
    item_by_id = {}
    
    # psets are deferred to the end so that all ids are resolved
    psets = []
    
    # same for entity attributes:
    entities = []
    
    # predefined types are just normal enumerations
    enumerations = {}
    
    pset_counts_by_stereo = defaultdict(int)
    
    for item in xmi_doc:
    
        item_by_id[item.id] = item

        depracated = False
        try: 
            if "DEPRECAT" in item.markdown:
                depracated = True
        except (AttributeError, TypeError):
            pass

        if not depracated:
            if item.type == "ENUM":
                enumerations[item.name] = item
            
            elif item.type == "PSET":
                psets.append(item)
                
                stereo = (item.node/"properties")[0].stereotype
                pset_counts_by_stereo[stereo] += 1
                # add human-readable name
                di["Name"] = caps_control(clean(normalise(re.sub("Pset_", "", item.name))).title())

            elif item.type == "ENTITY":
                by_id[item.id] = di = classes[item.name]
            
                st = item.meta.get('supertypes', [])
                if st:
                    di["Parent"] = st[0]
                di["Definition"] = strip_html(skip_empty(item.markdown), trim=True)
                # add human-readable name
                di["Name"] = caps_control(clean(normalise((item.name[3:] if item.name.lower().startswith('ifc') else item.name))).title())
                
                entities.append(item)
            di["Package"] = item.package # solely to split POT files

    for item in entities:
    
        if "IfcTypeObject" in xmi_doc.supertypes(item.id):
            continue
    
        predefined_type_attribute = [c for c in item.children if c.name == "PredefinedType"]
        if predefined_type_attribute:
            # NB this points to the EA extension node and not the packagedElement
            ptype = (predefined_type_attribute[0].node|"properties").type
            if ptype in enumerations:
                for c in enumerations[ptype].children:
                    if c.name not in ("USERDEFINED","NOTDEFINED"):
                        by_id[c.id] = di = classes[item.name + c.name]
                        di["Parent"] = item.name
                        di["Definition"] = strip_html(skip_empty(c.markdown), trim=True)
                        # add human-readable name, by identifying words in all-caps phrase (right now the words are hardcoded)
                        di["Name"] = caps_control(split_words(c.name).title())
                        di["Package"] = item.package # solely to split POT files

    for item in psets:
        refs = set(item.meta.get('refs') or [])
        
        for id in refs:
        
            if isinstance(id, tuple):
                # In case of TypeObject+PredefinedType appl
                # id = id[0]
                # what to do with typedrivenonly?
                # this option is disabled now
                assert False
                continue

            di = by_id.get(id)
            if di is None:
                try:
                    log_attr_2 = xmi_doc.xmi.by_id[id].name
                except KeyError as e:
                    log_attr_2 = id
                    print("WARNING: id %s not found" % id)
                    pass
                print("WARNING: for %s entity %s not emitted" % (item.name, log_attr_2))
                continue
            
            for a, (nm, (ty_ty_arg)) in zip(item.children, item.definition):
                
                # skip deprecated:
                depracated = False
                try: 
                    if "DEPRECAT" in a.markdown:
                        depracated = True
                except (AttributeError, TypeError):
                    pass

                if not depracated:
                    if item.stereotype == "QSET":
                        type_name = "real"
                        type_values = None
                        kind_name = 'Single'
                    else:
                        ty, ty_arg = ty_ty_arg
                        if ty == "PropertyEnumeratedValue":
                            type_name = list(ty_arg.values())[0]
                            enum_types_by_name = [c for c in xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:Class"] if c.name == type_name]
                            enum_types_by_name += [c for c in xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:Enumeration"] if c.name == type_name]
                            type_values = [x.name for x in enum_types_by_name[0]/"ownedLiteral"]
                            kind_name = 'Single'
                        else:
                            type_name = list(ty_arg.values())[0]
                            pe_types = [c for c in xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:Class"] if c.name == type_name]
                            pe_types += [c for c in xmi_doc.xmi.by_tag_and_type["packagedElement"]["uml:DataType"] if c.name == type_name]                    
                            pe_type = pe_types[0]
                            root_generalization = generalization(pe_type)
                            type_name = root_generalization.name.lower()
                            type_values = None
                            if ty == "PropertySingleValue":
                                kind_name = 'Single'
                            elif ty == "PropertyBoundedValue":
                                di["Psets"][item.name]["Properties"][a.name]["Description"] = "This property in IFC stores a bounded value, meaning it has a maximum of two (numeric or descriptive) values assigned, the first value specifying the upper bound and the second value specifying the lower bound. Read the IFC documentation for more information."
                                kind_name = 'Range'
                            elif ty == "PropertyReferenceValue":
                                di["Psets"][item.name]["Properties"][a.name]["Description"] = "This property in IFC takes as its value a reference to one of: IfcAddress, IfcAppliedValue, IfcExternalReference, IfcMaterialDefinition, IfcOrganization, IfcPerson, IfcPersonAndOrganization, IfcTable, IfcTimeSeries. Read the IFC documentation for more information."
                                kind_name = 'Complex'
                            elif ty == "PropertyListValue":
                                di["Psets"][item.name]["Properties"][a.name]["Description"] = "This property in IFC takes list as its value. Read the IFC documentation for more information."
                                kind_name = 'List'
                            elif ty == "PropertyTableValue":
                                di["Psets"][item.name]["Properties"][a.name]["Description"] = "This property in IFC takes a table as its value. That table has two columns (two lists), one for defining and other for defined values. Read the IFC documentation for more information."
                                kind_name = 'Complex'
                        # else:
                        #     print("Warning: %s.%s of type %s <%s> not mapped" % (item.name, nm, ty, ",".join(map(lambda kv: "=".join(kv), ty_arg.items()))))
                        #     continue
                            
                    di["Psets"][item.name]["Properties"][a.name]["Type"] = type_name
                    di["Psets"][item.name]["Properties"][a.name]["Name"] = caps_control(clean(normalise(a.name)).title())
                    # remove value explanation from the definition
                    di["Psets"][item.name]["Properties"][a.name]["Definition"] = re.sub(r":\s*[A-Z]{2,}.*", '...', strip_html(skip_empty(a.markdown), trim=True))
                    di["Psets"][item.name]["Properties"][a.name]["Kind"] = kind_name
                    di["Psets"][item.name]["Properties"][a.name]["Package"] = item.package # solely to split POT files

                    if type_values is None:
                        type_values = type_to_values.get(type_name)
                    if type_values:
                        di["Psets"][item.name]["Properties"][a.name]["Values"] = []
                        for tv in type_values:                       
                            # match the whole sentence containing the value, case insensitive
                            matches = re.findall(r"[^.;!,]*" + tv + r"[^.;!,]*", skip_empty(a.markdown), flags=re.IGNORECASE)
                            if matches:
                                description = clean(strip_html(matches[0].strip()))  #the whole sentence explaining the value
                            else:
                                description = caps_control(clean(normalise(split_words(tv))).title())  #the value but readable
                            di["Psets"][item.name]["Properties"][a.name]["Values"].append({"Value": tv,"Description":description,"Package":item.package})
                           
    for item in entities:
    
        item_name = item.name
        if item_name.endswith("Type"):
            item_name = item_name[:-4]
        di = classes[item_name]        
               
        for c in item.children:
        
            # skip deprecated:
            depracated = False
            try: 
                if "DEPRECAT" in c.markdown:
                    depracated = True
            except (AttributeError, TypeError):
                pass

            if not depracated:

                try:
                    node = c.node
                    if node.xml.tagName == "attribute":
                        node = xmi_doc.xmi.by_id[c.node.idref]
                        type_type = node|"type"
                        type_id = type_type.idref
                    else:
                        type_id = ([t for t in (node/"ownedEnd") if t.name == c.name][0]|"type").idref
                        type_type = xmi_doc.xmi.by_id[type_id]
                    type_item = item_by_id[type_id]
                except:
                    print("Not emitting %s.%s because of an error" % (item.name, c.name))
                    continue
                if c.name == "PredefinedType":
                    print("Not emitting %s.%s because it's the PredefinedType attribute" % (item.name, c.name))
                elif type_item.type == "ENTITY":
                    print("Not emitting %s.%s attribute because it's taking an ENTITY: %s" % (item.name, c.name, type_item.name))
                elif type_item.type == "SELECT":
                    print("Not emitting %s.%s attribute because it's taking a SELECT: %s" % (item.name, c.name, type_item.name))
                elif type_item.type == "TYPE":
                    
                    type_values = None
                    
                    if type_item.definition.super_verbatim:
                    
                        if not type_item.definition.super.lower().startswith("string"):                    
                            print("Not emitting %s.%s because it has a hardcoded express definition %s" % (item.name, c.name, type_item.definition.super))
                            continue
                        else:
                            type_name = "string"
                            
                    else:
                    
                        pattr = xmi_doc.xmi.by_id[c.node.idref]
                        ty_id = (pattr|"type").idref
                        ty_pe = xmi_doc.xmi.by_id[ty_id]
                        ty_gen = generalization(ty_pe)
                        type_name = ty_gen.name.lower()
                    
                    di["Psets"]["Attributes"]["Properties"][c.name]["Type"] = type_name
                    di["Psets"]["Attributes"]["Properties"][c.name]["Name"] = caps_control(clean(normalise(c.name)).title())
                    # remove value explanation from the definition
                    di["Psets"]["Attributes"]["Properties"][c.name]["Definition"] = re.sub(r":\s*[A-Z]{2,}.*", '...', strip_html(skip_empty(c.markdown), trim=True))
                    di["Psets"]["Attributes"]["Properties"][c.name]["Package"] = item.package # solely to split POT files
                    if type_values is None:
                        type_values = type_to_values.get(type_name)
                    if type_values:
                        di["Psets"]["Attributes"]["Properties"][c.name]["Values"] = []
                        for tv in type_values:
                            # match the whole sentence containing the value, case insensitive
                            # matches = re.findall(r"[^.;!,]*" + tv + r"[^.;!,]*", skip_empty(c.markdown), flags=re.IGNORECASE)
                            matches = re.findall(r"[^.;!,]*" + tv + r"[^.;!,]*", skip_empty(c.markdown), flags=re.IGNORECASE)
                            if matches:
                                description = clean(strip_html(matches[0].strip()))  #the whole sentence explaining the value
                            else:
                                description = caps_control(clean(normalise(split_words(tv))).title())  #the value but readable
                            di["Psets"]["Attributes"]["Properties"][c.name]["Values"].append({"Value": tv,"Description":description,"Package":item.package})                           

                elif type_item.type == "ENUM":
                
                    type_name = type_item.name
                    type_values = type_item.definition.values
                    di["Psets"]["Attributes"]["Properties"][c.name]["Type"] = type_name
                    # remove value explanation from the definition
                    di["Psets"]["Attributes"]["Properties"][c.name]["Definition"] = re.sub(r":\s*[A-Z]{2,}.*", '...', strip_html(skip_empty(c.markdown), trim=True))
                    di["Psets"]["Attributes"]["Properties"][c.name]["Values"] = []
                    di["Psets"]["Attributes"]["Properties"][c.name]["Package"] = item.package # solely to split POT files
                    for tv in type_values:                   
                        # match the whole sentence containing the value, case insensitive
                        # matches = re.findall(r"[^.;!,]*" + tv + r"[^.;!,]*", skip_empty(c.markdown), flags=re.IGNORECASE)
                        matches = re.findall(r"[^.;!,]*" + tv + r"[^.;!,]*", skip_empty(c.markdown), flags=re.IGNORECASE)
                        if matches:
                            description = clean(strip_html(matches[0].strip()))  #the whole sentence explaining the value
                        else:
                            description = caps_control(clean(normalise(split_words(tv))).title())  #the value but readable
                        di["Psets"]["Attributes"]["Properties"][c.name]["Values"].append({"Value": tv,"Description":description,"Package":item.package})
                else:
                    print("Not emitting %s.%s because it's a %s %s" % (item.name, c.name, type_item.name, type_item.type))

    # for x in sorted([item.name for item in psets]):
    #     print(x)
            
    for k, v in pset_counts_by_stereo.items():
        print(k + ":", v)
        
    print("TOTAL:", sum(pset_counts_by_stereo.values()))
            
    return classes

def filter_definition(di):

    children = defaultdict(list)    
    for k, v in di.items():
        if v.get("Parent"):
            children[v.get("Parent")].append(k)

    def parents(k):
        yield k
        v = di.get(k)
        if v and v.get('Parent'):
            yield from parents(v.get('Parent'))
            
    def child_or_self_has_psets(k):
        ps = di.get(k, {}).get("Psets")
        if ps:
            if set(ps.keys()) - {"Attributes"}:
                return True
        for c in children[k]:
            if child_or_self_has_psets(c):
                return True
        return False
        
    def has_child(k):
        def has_child_(k2):
            if k2 == k: return True
            if not children[k2]: return False
            return any(has_child_(c) for c in children[k2])
        return has_child_

    def should_include(k, v):
        # PREVIOUSLY return ("IfcProduct" in parents(k)) or has_child("IfcProduct")(k) or child_or_self_has_psets(k) 
        # right now 'has_pset' is broadening to include non-products that have psets, like IfcActor.
        return ("IfcRoot" in parents(k)) or ("IfcMaterialDefinition" in parents(k)) or ("IfcProfileDef" in parents(k)) or child_or_self_has_psets(k)
        
    return {k: v for k, v in di.items() if should_include(k, v)}
    

### Generate all the definitions:

defs = filter_definition(generate_definitions())

### go through names and add double square brackets in definitions:

#list all codes, so that we can later highlight them in the descriptions

def needs_bracket(s):
    if len(s) >= 6:
        if re.match(r'\b(?:[a-zA-Z]*[A-Z]){2,}[a-zA-Z]*\b', s):
            return True
        else:
            # not enough capital letters
            return False
    else:
        # too short
        return False
    

codes = [] #["USERDEFINED", "NOTDEFINED"]  # adding those two to be translatable values, as they occur in descriptions but will not be listed in bSDD.
for code, content in defs.items(): 
    if len(code) >= 6:
        codes.append(code)
    if content['Psets']:
        for pset_code, pset_content in content['Psets'].items():
            if needs_bracket(pset_code):
                codes.append(pset_code)
                for prop_code, prop_content in pset_content['Properties'].items():
                    if needs_bracket(prop_code):
                        codes.append(prop_code)
                    if prop_content['Values']:
                        for val in prop_content['Values']:
                            if needs_bracket(val['Value']):
                                codes.append(val['Value'])
all_codes = re.compile("\\b(%s)\\b" % "|".join(sorted(set(codes), key=lambda s: -len(s))))

# iterate again to annotate all descriptions and restructure classes/properties/values:
classes = []
props = []
to_translate = []
props_set = set()
for code, content in defs.items(): 
    clas_def = annotate(content['Definition'])
    classes.append({
        'Code': code,
        'Name': content['Name'],
        'Definition': clas_def,
        'Description': annotate(content['Description']),
        'ClassType': 'Class',
        'ClassProperties': []
    })
    to_translate.append({"msgid":code,"msgstr":content['Name'],"package":content['Package']})
    to_translate.append({"msgid":code+"_DEFINITION","msgstr":clas_def,"package":content['Package']})
    if content['Psets']:
        for pset_code, pset_content in content['Psets'].items():
            # TODO Right now, no place for PSET descriptions in bSDD, maybe GroupOfProperties.Definition?
            # if len(pset_content['Definition'])>0:
            #     pset_content['Definition'] = annotate(pset_content['Definition'])
            for prop_code, prop_content in pset_content['Properties'].items():
                name = skip_empty(prop_content['Name'])
                if not name:
                    name = normalise(prop_code)
                prop_def = annotate(prop_content['Definition'])
                classProp = {
                        "Code": prop_code, 
                        "Name": prop_content['Name'], 
                        "Definition": prop_def,
                        # "PropertyValueKind": prop_content['Type'],
                        }
                if prop_content['Values']:
                    classProp['AllowedValues'] = []
                    for val in prop_content['Values']:
                        descr = annotate(val['Description'])
                        classProp['AllowedValues'].append({
                            'Value': val['Value'],
                            'Description': descr
                        })
                        to_translate.append({"msgid":val['Value'],"msgstr":descr,"package":content['Package']})
                if not prop_code in props_set: 
                    # add to properties list, not just classProp
                    props_set.add(prop_code)
                    props.append(classProp)
                    to_translate.append({"msgid":prop_code,"msgstr":prop_content['Name'],"package":content['Package']})
                    to_translate.append({"msgid":prop_code+"_DEFINITION","msgstr":prop_def,"package":content['Package']})
                classProp['PropertySet'] = pset_code
                classes[-1]['ClassProperties'].append(classProp)


# TODO add value kind / type

### Generate IFC.json file:

bsdd_data = {
        'ModelVersion': '2.0',
        'OrganizationCode': 'buildingsmart',
        'DictionaryCode': 'ifc',
        'DictionaryName': 'IFC',
        'DictionaryVersion': '4.3.1',
        'LanguageIsoCode': 'EN',
        'LanguageOnly': False,
        'UseOwnUri': False,
        'License': 'CC BY-ND 4.0',
        'LicenseUrl': 'https://creativecommons.org/licenses/by-nd/4.0/legalcode',
        'MoreInfoUrl': 'https://ifc43-docs.standards.buildingsmart.org/',
        'QualityAssuranceProcedure': 'In general, IFC, or “Industry Foundation Classes”, is a standardized, digital description of the built environment, including buildings and civil infrastructure. It is an open, international standard (ISO 16739-1:2018), meant to be vendor-neutral, or agnostic, and usable across a wide range of hardware devices, software platforms, and interfaces for many different use cases. The IFC schema specification is the primary technical deliverable of buildingSMART International to fulfill its goal to promote openBIM®.',
        'QualityAssuranceProcedureUrl': 'https://technical.buildingsmart.org/standards/ifc/',
        'ReleaseDate': date.today().strftime(r'%Y-%m-%d'),
        'Classes': classes,
        'Properties': props
    }

#TODO add properties, now only ClassProps.

with open(output_dir, 'w', encoding='utf-8') as f:
    json.dump(bsdd_data, f, indent=4, default=lambda x: (getattr(x, 'to_json', None) or (lambda: vars(x)))(), ensure_ascii=False)


### Generate collection of .pot files in the "pot" folder:

class pot_file:
    def __init__(self, f):
        self.f = f
        now = date.today()
        print("""# Industry Foundation Classes IFC.
# Copyright (C) {year} buildingSMART
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: bsdd_support@buildingsmart.org\\n"
"POT-Creation-Date: {date} {time}\\n"
"X-Crowdin-SourceKey: msgstr\\n"
"Language-Team: buildingSMART community\\n"
""".format(year=now.strftime("%Y"), date=now.strftime(r"%Y-%m-%d"), time=now.strftime("%H:%M")), file=self.f)
        
    def __getattr__(self, k):
        return getattr(self.f, k)
        
class pot_dict(dict):
    def __missing__(self, key):      
        if not os.path.exists(os.path.join(output_dir, "pot")):
            os.makedirs(os.path.join(output_dir, "pot"))
        v = self[key] = pot_file(open(os.path.join(output_dir, "pot", key + ".pot"), "w+", encoding="utf-8")) # add folder: "pot", 
        return v


po_files = pot_dict()       

# for i, (package, (ln, col), p, d) in enumerate(generate_definitions()):
for t in to_translate:
    po_file = po_files[t['package']]   
    print("msgid", quote(t['msgid']),  file=po_file)
    print("msgstr", quote(t['msgstr']),  file=po_file)
    print(file=po_file)