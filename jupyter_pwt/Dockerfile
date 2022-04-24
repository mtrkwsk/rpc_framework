FROM jupyter/scipy-notebook

# RUN conda install --no-cache-dir --upgrade pip





# USER jovyan
# RUN pip install paho-mqtt
# RUN pip install numpy
# RUN pip install numexpr
# RUN pip install matplotlib
# RUN pip install coloredlogs
# RUN pip install tmux
# RUN pip install aquirdturtle_collapsible_headings
# RUN pip install jupyterlab-git
# RUN pip install nptdms
# RUN pip install net-tools

# RUN jupyter labextension install @jupyterlab/toc
# RUN pip install jupyter_dashboards
# RUN jupyter dashboards quick-setup --sys-prefix
# RUN pip install jupyterlab-interactive-dashboard-editor
# RUN pip install htop
# RUN pip install jupyterplot
# RUN pip install jupyter_dashboards
# RUN jupyter dashboards quick-setup --sys-prefix
# RUN conda install jupyterlab-git
# RUN jupyter serverextension enable --py jupyterlab_git
# RUN jupyter labextension install @jupyterlab/git


USER root
RUN apt-get update
RUN apt-get install -y git

USER jovyan
COPY requirements.txt ./
RUN pip install -r requirements.txt


# RUN conda install nbgitpuller 
# RUN jupyter serverextension enable --py nbgitpuller --sys-prefix 

WORKDIR /notebooks/

ENV GRANT_SUDO=yes
ENV JUPYTER_ENABLE_LAB=1
ENV JUPYTER_TOKEN=password
