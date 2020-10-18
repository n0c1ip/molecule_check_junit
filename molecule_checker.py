import subprocess
import os.path
from sys import exit
from subprocess import PIPE
from lxml import etree
import time

path_filter = "roles/base_"
changed_files = subprocess.run(["git", "diff", "HEAD", "HEAD~", "--name-only"], stdout=PIPE, stderr=PIPE)
molecule_default_sequence = ["lint", "destroy", "syntax", "create", "converge", "idempotence", "verify", "destroy"]
base_path = os.getcwd()
failed_test_exists = False


def get_changed_roles():
    roles_list = []
    list_files = changed_files.stdout.decode().splitlines()
    filtered_files = list(filter(lambda x: x.startswith(path_filter), list_files))
    for changed_file in filtered_files:
        role = changed_file.split(os.sep)
        roles_list.append(role[1])
    return roles_list, len(roles_list)


def molecule_check_role(role):
    print("Checking role " + role)
    os.chdir(base_path + "/roles/" + role)
    role_test = {
        "role": role,
        "tests": [],
        "passed_count": 0,
        "failed_count": 0,
    }
    for action in molecule_default_sequence:
        test = {
            "action": action,
            "passed": "",
            "stderr": "",
            "time": ""
        }
        print("Run action: " + action)
        start = time.time()
        molecule_test = subprocess.run(["molecule", action], stdout=PIPE, stderr=PIPE)
        elapsed = (time.time() - start)
        if molecule_test.returncode == 0:
            print("Molecule success step: " + action)
            role_test["passed_count"] += 1
            test["passed"] = bool(True)
            test["time"] = str(round(elapsed, 2))
            role_test["tests"].append(test)

        else:
            print("!!! Molecule error on step: " + action)
            global failed_test_exists
            failed_test_exists = True
            role_test["failed_count"] += 1
            test["passed"] = bool(False)
            test["stderr"] = molecule_test.stderr.decode()
            test["time"] = str(round(elapsed, 2))
            role_test["tests"].append(test)
            break
    return role_test


def generate_junit_xml(all_role_tests):
    testsuites = etree.Element("testsuites", name="Molecule testsuites")
    for role_test in all_role_tests:
        testsuite = etree.SubElement(testsuites, "testsuite",
                                     name="Role: " + role_test["role"],
                                     tests=str(len(role_test["tests"])), failures=str(role_test["failed_count"]))
        for test in role_test["tests"]:
            testcase = etree.SubElement(testsuite, "testcase",
                                        name="Role: " + role_test["role"] +
                                             ", Test action: " + test["action"], time=test["time"])
            if not test["passed"]:
                failure = etree.SubElement(testcase, "failure", message="Failed on step: " + test["action"])
                failure.text = str(test["stderr"])
    tree = etree.ElementTree(testsuites)
    os.chdir("../../")
    tree.write("junit-report.xml", encoding='utf8', method='xml', pretty_print=True)


def process_roles_testing(roles_t):
    all_roles_tests = []
    for role in roles_t:
        all_roles_tests.append(molecule_check_role(role))
    generate_junit_xml(all_roles_tests)


roles, roles_count = get_changed_roles()

if roles_count > 0:
    roles = list(set(roles))
    process_roles_testing(roles)
    if failed_test_exists:
        exit("Some test has failed state, exit with error")
else:
    print('Nothing to test')
