from agent import Agent
from agent.utils import get_argparser


def parse_args():
    return get_argparser().parse_args()


def main():
    args = parse_args()
    agent = Agent()
    agent.run(args)


if __name__ == '__main__':
    main()
