import grobid_tei_xml
import re
import xml.etree.ElementTree as ET


def xml_to_dict(xml_path):
    with open(xml_path, 'r') as xml_file:
        doc = grobid_tei_xml.parse_document_xml(xml_file.read())

    dict = doc.to_dict()

    # sample text is the json.body
    sample_text = dict["body"]

    def extract_section_text(tei_file_path):
        # Parse the XML file
        tree = ET.parse(tei_file_path)
        root = tree.getroot()

        # Define the namespace
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

        # Find the body element
        body = root.find('.//tei:body', ns)

        if body is None:
            return "Body element not found in the XML."

        # Extract main section headings, texts, and figures
        sections = {}
        figure_content = []  # For storing figures and other content
        note_content = []  # For storing notes and other content

        for elem in body.iter():

            # extract from divs
            if elem.tag == '{http://www.tei-c.org/ns/1.0}div':
                # find the head element
                head = elem.find('.//tei:head', ns)
                if head is not None:

                    # clean the section title
                    header_text = head.text
                    header_text = re.sub(r'\n', ' ', header_text)
                    header_text = re.sub(r'\s+', ' ', header_text)
                    header_text = re.sub(r'^\s', '', header_text)
                    header_text = re.sub(r'\s$', '', header_text)
                    header_text = header_text.strip()

                    # split at '. ', keep the second if exists
                    header_text = re.split(r'\. ', header_text)

                    if len(header_text) > 1:
                        header_text = header_text[1]
                    else:
                        header_text = header_text[0]

                    # make uppercase
                    header_text = header_text.lower()

                    section_title = header_text

                    

                    # section_title = head.text
                else:
                    section_title = 'No title'
                
                paragraphs = elem.findall('.//tei:p', ns)
                if paragraphs is not None:

                    for paragraph in paragraphs:
                        if section_title in sections:
                            sections[section_title] += paragraph.text
                        else:
                            sections[section_title] = paragraph.text


            # extract from figures
            elif elem.tag == '{http://www.tei-c.org/ns/1.0}figure':
                # Add figure details to other content
                fig_desc = elem.find('.//tei:figDesc', ns)
                figure_content.append(fig_desc.text if fig_desc is not None and fig_desc.text is not None else 'Figure without description')

            # extract from notes
            elif elem.tag == '{http://www.tei-c.org/ns/1.0}note':
                # Add figure details to other content
                note_text = elem.text
                note_content.append(note_text if note_text is not None else 'Note without description')



        
        # Add figures and other content to the sections dictionary
        sections['figures'] = ' '.join(figure_content)
        sections['notes'] = ' '.join(note_content)

        return sections

    dict["sections"] = extract_section_text(xml_path)

    return dict


# xml_path = r"./db/grobidXML/ASE/10.1109\ASE.1997.632821.tei.xml"