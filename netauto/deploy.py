import yaml
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"),
                  trim_blocks=True, lstrip_blocks=True)

def deploy_task(conn, dev, template, vars_file, dry_run=False):
    variables = yaml.safe_load(open(vars_file))
    lines = env.get_template(template).render(**variables, dev=dev).splitlines()
    lines = [l for l in lines if l.strip()]
    if dry_run:
        return lines
    out = conn.send_config_set(lines)
    conn.save_config()
    return out
