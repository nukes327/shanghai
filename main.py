import logging
import logging.config

import shanghai.shanghai as shanghai

if __name__ == '__main__':
    logging.config.fileConfig('config/logging.ini')
    logger = logging.getLogger(__name__)
    doll = shanghai.Bot()
