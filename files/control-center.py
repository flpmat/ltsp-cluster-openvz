#/usr/bin/python
import pgdb, os, sys

#FIXME: This should be a configuration file
db_user="ltsp"
db_password="ltspcluster"
db_host="localhost"
db_database="ltsp"

#Init DB
db=pgdb.connect(user=db_user,password=db_password,host=db_host,database=db_database)
cursor=db.cursor()

def Cleanup():
    "Reset all temporary tables"

    cursor.execute("TRUNCATE status;")
    db.commit()
    print "Cleaned status table"

    cursor.execute("TRUNCATE log;")
    cursor.execute("ALTER SEQUENCE log_id_key_seq RESTART WITH 1;")
    db.commit()
    print "Cleaned log table"

    cursor.execute("TRUNCATE computershw;")
    db.commit()
    print "Cleaned computershw table"

def Rebuild():
    "Rebuild the nodes tree"

    cursor.execute("SELECT rebuild_tree()")
    db.commit()
    print "Regenerated tree"

def CleanAttributes(attr_list):
    "Remove all attributes, keeping only the ones in attr_list"

    where=''
    for attr in attr_list:
        if where == '':
            where+="name != '"+attr+"'"
        where+=" AND name != '"+attr+"'"
    cursor.execute("SELECT id FROM attributesdef WHERE "+where)
    items=cursor.fetchall()
    for item in items:
        cursor.execute("DELETE FROM attributes WHERE attributesdef_id='"+str(item[0])+"'")
        cursor.execute("DELETE FROM attributesdefdict WHERE attributesdef_id='"+str(item[0])+"'")
        cursor.execute("DELETE FROM attributesselect WHERE attributesdef_id='"+str(item[0])+"'")
    cursor.execute("DELETE FROM attributesdef WHERE "+where)
    db.commit()

def UpdateAttributes():
    "Open an attribute definition file and update the attribute list from it"

    if len(sys.argv) < 2:
        print "ERROR: You need to specify a configuration file"
        return None
    if not os.path.exists(sys.argv[1]):
        print "ERROR: File doesn't exist"
        return None

    config=open(sys.argv[1],"r")
    attr_list=set()

    for line in config.readlines():
        attr_name, attr_type=line.strip().split(" => ") #FIXME: We should handle bogus config file here
        attr_list.add(attr_name)
        cursor.execute("SELECT id FROM attributesdef WHERE name='"+attr_name+"'")

        # Add missing attributes
        if len(cursor.fetchall()) == 0:
            if attr_type == "text":
                cursor.execute("INSERT INTO attributesdef (name) VALUES ('"+attr_name+"')")
            elif attr_type == "multilist":
                cursor.execute("INSERT INTO attributesdef (name,attributetype) VALUES ('"+attr_name+"','2')")
            elif attr_type.startswith("list"):
                list=attr_type.replace("list:","").split(",")
                cursor.execute("INSERT INTO attributesdef (name,attributetype) VALUES ('"+attr_name+"','1')")
                cursor.execute("SELECT id FROM attributesdef WHERE name='"+attr_name+"'")
                attr_id=cursor.fetchall()[0][0]
                for value in list:
                    cursor.execute("INSERT INTO attributesdefdict (attributesdef_id,value,sortval) VALUES ('"+str(attr_id)+"','"+value+"','0')")
            db.commit()
        else:
            #FIXME: Updating attribute type should happen here
            pass

    #Drop removed attributes
    CleanAttributes(attr_list)
    config.close()

def ReorderDatabase():
    # Clean all temporary tables to make sure we don't have constraint conflict there
    Cleanup()

    # Drop all contraints for now
    cursor.execute("ALTER TABLE attributes DROP CONSTRAINT attributes_attributesdef_id_fkey;")
    cursor.execute("ALTER TABLE attributesdefdesc DROP CONSTRAINT attributesdefdesc_attributesdef_id_fkey;")
    cursor.execute("ALTER TABLE attributesdefdict DROP CONSTRAINT attributesdefdict_attributesdef_id_fkey;")
    cursor.execute("ALTER TABLE attributesselect DROP CONSTRAINT attributesselect_attributesdef_id_fkey;")
    db.commit()

    # Reorder attributesdef
    cursor.execute("SELECT id FROM attributesdef ORDER BY id ASC")
    attributes=cursor.fetchall()
    attr_id=0
    for attribute in attributes:
        attr_id+=1
        cursor.execute("UPDATE attributes SET attributesdef_id='"+str(attr_id)+"' WHERE attributesdef_id='"+str(attribute[0])+"'")
        cursor.execute("UPDATE attributesdefdesc SET attributesdef_id='"+str(attr_id)+"' WHERE attributesdef_id='"+str(attribute[0])+"'")
        cursor.execute("UPDATE attributesdefdict SET attributesdef_id='"+str(attr_id)+"' WHERE attributesdef_id='"+str(attribute[0])+"'")
        cursor.execute("UPDATE attributesselect SET attributesdef_id='"+str(attr_id)+"' WHERE attributesdef_id='"+str(attribute[0])+"'")
        cursor.execute("UPDATE attributesdef SET id='"+str(attr_id)+"' WHERE id='"+str(attribute[0])+"'")
        db.commit()

    # Restore the constraints
    cursor.execute("ALTER TABLE attributes ADD CONSTRAINT attributes_attributesdef_id_fkey FOREIGN KEY (attributesdef_id) REFERENCES attributesdef(id) ON UPDATE CASCADE;")
    cursor.execute("ALTER TABLE attributesdefdesc ADD CONSTRAINT attributesdefdesc_attributesdef_id_fkey FOREIGN KEY (attributesdef_id) REFERENCES attributesdef(id) ON UPDATE CASCADE;")
    cursor.execute("ALTER TABLE attributesdefdict ADD CONSTRAINT attributesdefdict_attributesdef_id_fkey FOREIGN KEY (attributesdef_id) REFERENCES attributesdef(id) ON UPDATE CASCADE;")
    cursor.execute("ALTER TABLE attributesselect ADD CONSTRAINT attributesselect_attributesdef_id_fkey FOREIGN KEY (attributesdef_id) REFERENCES attributesdef(id) ON UPDATE CASCADE;")
    db.commit()

#FIXME: This should be implemented using parameters
Cleanup()
UpdateAttributes()
ReorderDatabase()
Rebuild()

#Close DB
db.close()
