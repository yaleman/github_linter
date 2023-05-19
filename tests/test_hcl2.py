""" tests things interacting with HCL-format files (terraform, hopefully)"""


import hcl2  # type: ignore


def test_load_basic_hcl2() -> None:
    """tests loading an example file"""
    examplefile = """terraform {
    backend "s3" {
        bucket = "example-bucket"
        key        = "terraform.tfstate"
        region = "us-east-1"
    }
}"""

    value = hcl2.loads(examplefile)

    assert value["terraform"]
    print(value["terraform"])
